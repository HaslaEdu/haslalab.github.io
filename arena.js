/* HaslaLab accounts, monthly problems, grading and rankings (front end).
   The account is the community account (same server, same sign-in token).  Routes:
     #/login  #/signup  #/me          sign in, sign up, my record
     #/monthly[/<YYYY-MM>]            monthly problems (old #/weekly links still work)
     #/monthly/p/<id>                 one problem: type the answer or photograph it (OCR), get it graded
     #/rank[/<month|all>]             rankings
     #/monthly/admin                  admins: add problems, grade what waits; exam tokens and marking schemes
     #/lab  #/lab/<id>                exam mode (sim/exam.html): my tokens and exams, one exam's marks and pages
   Uses cmApi, cmTok, cm, esc, lang and CMT from index.html. */
"use strict";
const AT = {
  ko: {nav: "월별 문제", login: "로그인", signup: "회원가입", me: "내 기록", logout: "로그아웃",
       weekH: "월별 문제", weekSub: "월별로 문제를 모아 풉니다. 마감 전에 제출한 답은 해당 월 랭킹에 반영되고, 마감 후에는 풀이가 공개됩니다. 마감 시각은 한국 시각 기준입니다.",
       closesIn: "마감까지", deadline: "마감", closed: "마감", opens: "열림", short: "단답", essay: "서술", pts: "점", level: "난이도", users: "명 도전", solvers: "명 만점",
       best: "내 최고", pending: "채점 대기", ai_suspected: "AI 작성 의심 · 채점 보류", solve: "풀기", archive: "지난 월별 문제", rank: "랭킹", rankWeek: "월별", rankAll: "전체", rankH: "랭킹",
       rankSub: "월별 랭킹은 마감 전에 제출한 답의 문제별 최고 점수를 더합니다(같으면 먼저 닿은 사람이 앞). 전체 랭킹은 레이팅 순입니다.",
       ratingHelp: "레이팅 = 푼 문제 중 어려운 100문제의 난이도 점수 합 + 푼 문제 수 보너스. 단답은 정답, 서술형은 80% 이상이면 푼 문제로 칩니다. 지난 월별 문제도 풀면 레이팅에 들어갑니다.",
       rating: "레이팅", nextTier: "다음 티어까지", solvedN: "푼 문제",
       nick: "닉네임", total: "점수", solved: "푼 문제", tier: "티어", empty: "아직 기록이 없습니다.", top: "해당 월 상위",
       answer: "답", answerPh: "숫자만 쓰세요 (예: 1.79)", essayPh: "풀이를 쓰세요. 수식은 $...$ 안에 LaTeX로 쓰거나 그냥 글로 써도 됩니다.",
       photo: "답안 사진 올리기", photoHint: "종이에 쓴 풀이를 찍어 올리면 글자로 읽어 줍니다(OCR). 읽은 글을 꼭 확인하고 고친 뒤 제출하세요.",
       mathMode: "수식이 많은 답안 (수식을 LaTeX로 읽기)", reading: "사진을 읽는 중…", readDone: "사진을 읽었습니다. 아래 글이 답안과 같은지 확인하고 고친 뒤 제출하세요.",
       scanPreparing: "사진의 기울기와 그림자를 보정하는 중…", scanCheck: "글씨와 수식이 잘리지 않았는지 확인한 뒤 읽기를 누르세요.",
       scanOriginal: "촬영 원본", scanClean: "보정 사진", scanRead: "이 사진으로 읽기", scanRetake: "다른 사진", scanCancel: "취소",
       scanFailed: "사진 보정에 실패했습니다. 촬영 원본을 확인하거나 다른 사진을 골라주세요.", scanUnavailable: "이 브라우저에서는 사진을 보정할 수 없습니다. 촬영 원본을 확인해 주세요.",
       scanWeak: "종이 모서리를 확실하게 찾지 못했습니다. 잘린 글씨가 있으면 촬영 원본을 선택하거나 다시 찍어주세요.",
       scanBlur: "사진이 흐립니다. 작은 수식과 첨자가 보이지 않으면 다시 찍어주세요.", scanSmall: "사진 해상도가 낮습니다. 작은 수식과 첨자가 보이도록 더 가까이 찍어주세요.",
       scanLong: "읽은 글이 답안 길이 제한을 넘었습니다. 아래 글을 확인하고 12,000자 이내로 정리한 뒤 제출하세요.",
       preview: "미리보기", submit: "제출하고 채점받기", grading: "채점 중… (서술형은 30초쯤 걸립니다)", loginToSubmit: "로그인하면 제출하고 채점받을 수 있습니다.",
       result: "채점 결과", score: "점수", criteria: "채점 항목", evidence: "근거", feedback: "첨삭", good: "잘한 점", fix: "고칠 점",
       met: "충족", partial: "부분", not_met: "미충족", uncertain: "불확실", right: "정답입니다", wrong: "오답입니다",
       pendingNote: "답안이 접수되어 채점을 기다리고 있습니다. 채점 결과는 여기와 랭킹에 반영됩니다.",
       errorNote: "채점 서버가 응답하지 않았습니다. 답안은 저장되었고 관리자가 다시 채점합니다.",
       evidenceIssue: "답안에 없는 내용을 근거로 든 항목은 0점으로 처리했습니다.",
       mine: "내 제출", solution: "풀이", solutionLater: "풀이는 해당 월 문제의 마감 후 공개됩니다.", grader: "채점",
       viaOcr: "사진에서 읽음", practice: "연습(랭킹 제외)", noProblems: "해당 월 문제가 아직 없습니다.",
       oldServer: "월별 문제 서버가 아직 업데이트되지 않았습니다. 잠시 후 다시 와 주세요.", ocrOff: "사진 인식(OCR)이 아직 서버에 연결되지 않았습니다. 답을 직접 입력해 주세요.",
       myH: "내 기록", myRank: "전체 순위", myTotal: "총점", mySolved: "만점 문제", recent: "최근 제출", settings: "계정 설정(비밀번호 · 탈퇴)",
       admin: "관리", addP: "문제 추가 / 고치기", queue: "채점 대기열", save: "저장", saved: "저장했습니다", giveScore: "점수 주기", regrade: "AI로 다시 채점",
       oauthWith: {google: "Google로 계속하기", kakao: "카카오로 계속하기", naver: "네이버로 계속하기", github: "GitHub로 계속하기", discord: "Discord로 계속하기"}, oauthOr: "또는 아이디로", oauthOff: "관리자가 아직 연결하지 않았습니다",
       oauthNew: "가입했습니다. 닉네임은 계정 이름에서 가져왔으니, 원하면 아래에서 바꾸세요.", linked: "연결했습니다", linkH: "연결된 로그인", link: "연결하기", connected: "연결됨",
       nickH: "닉네임 바꾸기", change: "바꾸기", pwSet: "비밀번호 만들기 (아이디로도 로그인)", pwNew: "새 비밀번호 (8자 이상)", done: "바꿨습니다",
       tiers: {bronze: "브론즈", silver: "실버", gold: "골드", platinum: "플래티넘", diamond: "다이아몬드", ruby: "루비", master: "마스터", unrated: "Unrated"},
       err: {bad_answer: "답을 입력하세요.", bad_image: "JPEG, PNG, WebP 사진 한 장만 올릴 수 있습니다.", image_too_big: "사진이 너무 큽니다(8 MB까지).",
             ocr_empty: "사진에서 글씨를 찾지 못했습니다. 원본을 확인하거나 더 선명하게 다시 찍어주세요.",
             ocr_image_too_big: "글씨의 선명도를 유지하면서 사진 용량을 줄이지 못했습니다. 종이가 화면을 채우게 다시 찍어주세요.",
             ocr_off: "사진 인식(OCR)이 아직 서버에 연결되지 않았습니다.", ocr_failed: "사진을 읽지 못했습니다. 더 밝고 반듯하게 찍어 보세요.", rate_limited: "요청이 너무 많습니다. 내일 다시 시도해 주세요.",
             forbidden: "관리자만 할 수 있습니다.", bad_code: "로그인 링크가 만료되었습니다. 다시 시도해 주세요.", oauth_off: "이 로그인은 아직 연결되지 않았습니다.",
             oauth_failed: "외부 로그인에 실패했습니다. 다시 시도해 주세요.", oauth_cancelled: "로그인을 취소했습니다.", oauth_in_use: "그 계정은 이미 다른 HaslaLab 계정에 연결되어 있습니다.", bad_week: "월은 2026-11 형식으로 쓰세요.", bad_rubric: "채점 기준(JSON)을 확인하세요.", bad_kind: "유형을 고르세요."}},
  en: {nav: "Monthly", login: "Sign in", signup: "Sign up", me: "My record", logout: "Sign out",
       weekH: "Problems of the month", weekSub: "Problems are grouped by month. Answers submitted before the deadline count towards that month's rankings; solutions are published after the deadline. All deadlines use Korean time (KST).",
       closesIn: "Closes in", deadline: "Deadline", closed: "Closed", opens: "Opened", short: "Short answer", essay: "Written", pts: "pts", level: "Level", users: "tried", solvers: "full marks",
       best: "My best", pending: "Waiting", ai_suspected: "Suspected AI writing · not graded", solve: "Solve", archive: "Past monthly problems", rank: "Rankings", rankWeek: "Monthly", rankAll: "All time", rankH: "Rankings",
       rankSub: "The monthly ranking adds your best score on each problem submitted before its deadline (ties go to whoever got there first). All time ranks by rating.",
       ratingHelp: "Rating = the difficulty points of your 100 hardest solved problems plus a bonus for the number solved. A short answer counts when right, a written one at 80 % or more. Past monthly problems count too.",
       rating: "Rating", nextTier: "to the next tier", solvedN: "Solved",
       nick: "Name", total: "Score", solved: "Solved", tier: "Tier", empty: "No results yet.", top: "Top this month",
       answer: "Answer", answerPh: "A number only (e.g. 1.79)", essayPh: "Write your solution. Put formulas in $...$ as LaTeX, or just write them out.",
       photo: "Upload a photo of your answer", photoHint: "Photograph your written solution and it is read into text (OCR). Check and correct the text before you submit.",
       mathMode: "Answer with many formulas (read them as LaTeX)", reading: "Reading the photo…", readDone: "The photo has been read. Check that the text below matches your answer, correct it, then submit.",
       scanPreparing: "Straightening the photo and removing shadows…", scanCheck: "Check that no writing or formulas were cut off, then read this photo.",
       scanOriginal: "Original photo", scanClean: "Straightened photo", scanRead: "Read this photo", scanRetake: "Choose another", scanCancel: "Cancel",
       scanFailed: "The photo could not be straightened. Check the original photo or choose another.", scanUnavailable: "This browser cannot straighten photos. Check the original photo before reading it.",
       scanWeak: "The page corners were not found for certain. If any writing is cut off, use the original photo or take another.",
       scanBlur: "The photo is blurred. Take another if small formulas or subscripts are unclear.", scanSmall: "The photo has low resolution. Move closer so small formulas and subscripts are clear.",
       scanLong: "The recognized text exceeds the answer limit. Check the text below and shorten it to 12,000 characters before submitting.",
       preview: "Preview", submit: "Submit and grade", grading: "Grading… (a written answer takes about 30 s)", loginToSubmit: "Sign in to submit and be graded.",
       result: "Result", score: "Score", criteria: "Criteria", evidence: "Evidence", feedback: "Comments", good: "Good", fix: "To fix",
       met: "met", partial: "partly", not_met: "not met", uncertain: "unsure", right: "Correct", wrong: "Not correct",
       pendingNote: "Your answer has been accepted and is waiting to be graded. Its result will appear here and in the rankings.",
       errorNote: "The grading server did not answer. Your answer is saved and an admin will grade it.",
       evidenceIssue: "Criteria whose evidence was not in your answer were given 0.",
       mine: "My submissions", solution: "Solution", solutionLater: "The solution is published after this month's deadline.", grader: "Graded by",
       viaOcr: "read from a photo", practice: "practice (not ranked)", noProblems: "No problems for this month yet.",
       oldServer: "The monthly-problem server has not been updated yet. Please come back shortly.", ocrOff: "Photo reading (OCR) is not connected yet. Please type your answer.",
       myH: "My record", myRank: "Overall rank", myTotal: "Total", mySolved: "Full marks", recent: "Recent submissions", settings: "Account settings (password, delete)",
       admin: "Admin", addP: "Add / edit a problem", queue: "Grading queue", save: "Save", saved: "Saved", giveScore: "Give score", regrade: "Regrade with AI",
       oauthWith: {google: "Continue with Google", github: "Continue with GitHub", discord: "Continue with Discord", kakao: "Continue with Kakao", naver: "Continue with NAVER"}, oauthOr: "or with a username", oauthOff: "not connected by the admin yet",
       oauthNew: "Welcome! Your nickname was taken from that account; change it below if you like.", linked: "Connected", linkH: "Sign-in methods", link: "Connect", connected: "connected",
       nickH: "Change nickname", change: "Change", pwSet: "Create a password (to sign in with your username too)", pwNew: "New password (8+ characters)", done: "Changed",
       tiers: {bronze: "Bronze", silver: "Silver", gold: "Gold", platinum: "Platinum", diamond: "Diamond", ruby: "Ruby", master: "Master", unrated: "Unrated"},
       err: {bad_answer: "Enter an answer.", bad_image: "Only one JPEG, PNG or WebP photo.", image_too_big: "The photo is too large (8 MB max).",
             ocr_empty: "No writing was found. Check the original or take a clearer photo.",
             ocr_image_too_big: "The photo could not be made smaller while keeping the writing clear. Take another with the page filling the frame.",
             ocr_off: "Photo reading (OCR) is not connected yet.", ocr_failed: "The photo could not be read. Try a brighter, straighter shot.", rate_limited: "Too many requests. Try again tomorrow.",
             forbidden: "Admins only.", bad_code: "The sign-in link has expired. Please try again.", oauth_off: "That sign-in is not connected yet.",
             oauth_failed: "The outside sign-in failed. Please try again.", oauth_cancelled: "Sign-in was cancelled.", oauth_in_use: "That account is already connected to another HaslaLab account.", bad_week: "Write the month as 2026-11.", bad_rubric: "Check the rubric JSON.", bad_kind: "Choose a kind."}}};
/* tiers after solved.ac: level 1–30 is Bronze V … Ruby I, 31 Master, 0 unrated */
const TIER_KEYS = ["bronze", "silver", "gold", "platinum", "diamond", "ruby"];
const TIER_COL = {bronze: "#ad5600", silver: "#435f7a", gold: "#ec9a00", platinum: "#27e2a4", diamond: "#00b4fc", ruby: "#ff0062", master: "#b300e0", unrated: "#2d2d2d"};
const ROMAN = ["V", "IV", "III", "II", "I"];
function tierKey(lv) { return lv >= 31 ? "master" : lv >= 1 ? TIER_KEYS[Math.floor((lv - 1) / 5)] : "unrated"; }
function tierName(lv, short) {
  const k = tierKey(lv), T = arT();
  if (k === "master" || k === "unrated") return short ? (k === "master" ? "M" : "–") : T.tiers[k];
  const r = ROMAN[(lv - 1) % 5];
  return short ? k[0].toUpperCase() + (5 - (lv - 1) % 5) : T.tiers[k] + " " + r;
}
/* the little shield solved.ac draws, in the tier's colour, with the step number inside */
function tierIcon(lv, size) {
  const c = TIER_COL[tierKey(lv)], n = lv >= 1 && lv <= 30 ? 5 - (lv - 1) % 5 : lv >= 31 ? "M" : "?";
  return `<svg class="artico" width="${size || 18}" height="${(size || 18) * 1.15}" viewBox="0 0 20 23" aria-hidden="true"><path d="M10 .8 19 5.2v6.9c0 5-3.7 8.6-9 10.1C4.7 20.7 1 17.1 1 12.1V5.2z" fill="${c}"/>
    <path d="M10 2.6 17.3 6.2v5.9c0 4.1-3 7.1-7.3 8.4-4.3-1.3-7.3-4.3-7.3-8.4V6.2z" fill="#fff" opacity=".18"/><text x="10" y="15.4" text-anchor="middle" font-size="10" font-weight="800" fill="#fff" font-family="system-ui,sans-serif">${n}</text></svg>`;
}
const ar = {seq: 0, health: null};
const arT = () => AT[lang];
const arErr = (e) => (arT().err[e && e.code]) || cmErr(e);
function arTier(lv) { return `<span class="artier" style="--c:${TIER_COL[tierKey(lv)]}">${tierIcon(lv, 14)}${esc(tierName(lv))}</span>`; }
function arLevel(lv) { return `<span class="arlvl" title="${esc(tierName(lv))}">${tierIcon(lv, 15)}</span>`; }
function arLeft(sec) { if (sec <= 0) return arT().closed; const d = Math.floor(sec / 86400), h = Math.floor(sec % 86400 / 3600), m = Math.floor(sec % 3600 / 60);
  return lang === "ko" ? (d ? d + "일 " : "") + h + "시간 " + m + "분" : (d ? d + "d " : "") + h + "h " + m + "m"; }
const arIsMonth = value => /^\d{4}-(?:0[1-9]|1[0-2])$/.test(value || "");
const arIsPeriod = value => arIsMonth(value) || /^\d{4}-W\d{2}$/.test(value || "");
const arPeriodId = value => typeof value === "string" ? value : value?.period || value?.month || value?.week || "";
const arPeriodQuery = value => arIsPeriod(value) ? "&" + (arIsMonth(value) ? "month=" : "week=") + encodeURIComponent(value) : "";
function arPeriodLabel(value) {
  const period = arPeriodId(value);
  if (!arIsMonth(period)) return period;
  const [year, month] = period.split("-").map(Number);
  return lang === "ko" ? `${year}년 ${month}월` : new Intl.DateTimeFormat("en", {year: "numeric", month: "long", timeZone: "Asia/Seoul"}).format(new Date(Date.UTC(year, month - 1, 1)));
}
function arDate(s) { const D = new Date((s + 9 * 3600) * 1000); return (D.getUTCMonth() + 1) + "." + D.getUTCDate(); }
function arDeadline(s) {
  const D = new Date((s - 1 + 9 * 3600) * 1000), pad = n => String(n).padStart(2, "0");
  return `${D.getUTCFullYear()}.${pad(D.getUTCMonth() + 1)}.${pad(D.getUTCDate())} ${pad(D.getUTCHours())}:${pad(D.getUTCMinutes())} ${lang === "ko" ? "(한국 시각)" : "KST"}`;
}
/* text with $...$ formulas: escaped, line breaks kept; KaTeX renders it afterwards */
function arText(s) { return esc(s || "").replace(/\n/g, "<br>"); }
/* Published problems have a deliberately small, escaped format. Student answers keep arText.
   Only repository-owned weekly diagrams are permitted; HTML and remote image URLs stay text. */
function arPublishedText(s) {
  const prose = text => {
    const blocks = [], lines = [];
    const flush = () => { if (lines.length) blocks.push(`<p>${lines.splice(0).map(esc).join("<br>")}</p>`); };
    for (const line of text.replace(/\r\n?/g, "\n").split("\n")) {
      const heading = /^(#{2,3})\s+(.+)$/.exec(line);
      const figure = /^!\[([^\]\n]{1,300})\]\((weekly\/figures\/[a-z0-9][a-z0-9-]*\.svg)\)$/.exec(line);
      if (!line.trim()) { flush(); }
      else if (heading) { flush(); const level = heading[1].length; blocks.push(`<h${level}>${esc(heading[2])}</h${level}>`); }
      else if (figure) { flush(); const svg = typeof HL_MONTHLY_FIGURES !== "undefined" && HL_MONTHLY_FIGURES.render(figure[2]); blocks.push(`<figure class="arfigure">${svg || `<img src="${figure[2]}" alt="${esc(figure[1])}" loading="lazy" decoding="async">`}<figcaption>${esc(figure[1])}</figcaption></figure>`); }
      else lines.push(line);
    }
    flush(); return blocks.join("\n");
  };
  return String(s || "").split(/(\$\$[\s\S]*?\$\$)/).map(part => part.startsWith("$$") && part.endsWith("$$")
    ? `<div class="arformula">${esc(part)}</div>` : prose(part)).join("\n");
}
let arKatex = null;
function arMath(el) {
  if (!el) return;
  const go = () => { try { window.renderMathInElement(el, {delimiters: [{left: "$$", right: "$$", display: true}, {left: "$", right: "$", display: false}], throwOnError: false}); } catch (e) {} };
  if (window.renderMathInElement) return go();
  if (!arKatex) arKatex = new Promise((res) => {
    const base = "vendor/katex/",                                  /* KaTeX 0.16.9, MIT, kept in the site */ l = document.createElement("link"); l.rel = "stylesheet"; l.href = base + "katex.min.css"; document.head.append(l);
    const s1 = document.createElement("script"); s1.src = base + "katex.min.js"; s1.onload = () => { const s2 = document.createElement("script"); s2.src = base + "contrib/auto-render.min.js"; s2.onload = res; document.head.append(s2); }; document.head.append(s1);
  });
  arKatex.then(go);
}

/* ── the account chip in the header, on every page ── */
async function arChip() {
  let box = document.getElementById("acct");
  if (!box) { const l = document.querySelector("header .lang"); if (!l) return; box = document.createElement("div"); box.id = "acct"; box.className = "acct"; l.before(box); }
  await cmLoadMe();
  const T = arT();
  box.innerHTML = cm.me
    ? `<a href="#/me" class="acct-me" title="${esc(T.me)}">${cmAv(cm.me.nickname, "s", cm.me.avatar)}<span>${esc(cm.me.nickname)}</span></a>`
    : `<a href="#/login" class="acct-in" data-ar="login">${T.login}</a>`;
  const a = box.querySelector("[data-ar=login]"); if (a) a.onclick = () => { try { sessionStorage.setItem("hlCmBack", location.hash); } catch (e) {} };
}

function viewArena(first) { return `<div class="shell cm ar"><div id="arRoot" data-r="${esc(first)}"><div class="cmnote">…</div></div></div>`; }
/* Cached HTML can load a newer lazy arena file while its inline helpers are still old. */
function arPageRead(path) {
  if(typeof cmPageRead==='function')return cmPageRead(path);
  const scope=cmIdentityScope();
  if(cm.meScope!==scope){cm.me=null;cm.meChecked=false;}cm.meScope=scope;
  const p=cmApi('GET',path).then(r=>{
    if(cmIdentityScope()!==scope)throw{code:'account_changed'};
    if(Object.prototype.hasOwnProperty.call(r,'user')){cm.me=r.user;cm.meChecked=true;}
    if(r.api_version)cm.v=r.api_version;
    return r;
  });
  const identity=p.then(r=>{
    if(Object.prototype.hasOwnProperty.call(r,'user'))return r.user;
    if(cmMeP===identity)cmMeP=null;
    return cmLoadMe();
  }).catch(()=>null).finally(()=>{if(cmMeP===identity)cmMeP=null;});
  cmMeP=identity;return p;
}
function arMeOverview() {
  if(typeof cmMeOverview==='function')return cmMeOverview();
  const scope=cmIdentityScope();
  if(ar.overviewP?.scope===scope)return ar.overviewP.promise;
  if(cm.meScope!==scope){cm.me=null;cm.meChecked=false;}cm.meScope=scope;
  const p=cmApi('GET','/me/overview').catch(async error=>{
    if(error.status!==404)throw error;
    if(cmIdentityScope()!==scope)throw{code:'account_changed'};
    const [identity,stats,ids,active,health]=await Promise.all([
      cmApi('GET','/me'),cmApi('GET','/me/stats'),cmApi('GET','/me/identities'),
      cmApi('GET','/lab/active').catch(e=>{if(e.status===404)return null;throw e;}),cmHealth()
    ]);
    return{user:identity.user,stats,identities:ids.identities,providers:ids.providers,has_password:ids.has_pw,active:active?.active,tokens:active?.tokens,health};
  }).then(r=>{
    if(cmIdentityScope()!==scope)throw{code:'account_changed'};
    cm.me=r.user;cm.meChecked=true;
    if(r.health){ar.health=r.health;cm.v=r.health.v||cm.v;cmHealthBase=cmBase();cmHealthUntil=Date.now()+600000;cmHealthP=Promise.resolve(r.health);}
    return r;
  }).finally(()=>{if(ar.overviewP?.promise===p)ar.overviewP=null;});
  ar.overviewP={scope,promise:p};
  const identity=p.then(r=>cmIdentityScope()===scope?r.user:null).catch(()=>null).finally(()=>{if(cmMeP===identity)cmMeP=null;});
  cmMeP=identity;return p;
}
async function arMount() {
  const root = document.getElementById("arRoot"); if (!root) return;
  const my = ++ar.seq,scope=cmIdentityScope(),currentLang=lang,routeAlive=()=>my === ar.seq && document.getElementById("arRoot") === root && lang===currentLang, alive = () => routeAlive() && cmIdentityScope()===scope;
  const parts = location.hash.replace(/^#\/?/, "").split("?")[0].split("/").filter(Boolean), [a, b, c] = parts;
  ar.poller?.dispose();ar.poller=null;let bootstrap=null,primary=null,version=0;
  const weekly=(a==='monthly'||a==='weekly')&&b!=='p'&&b!=='admin',problem=(a==='monthly'||a==='weekly')&&b==='p'&&/^\d+$/.test(c||'');
  if(weekly||problem||a==='rank'){
    const path=problem?'/problems/'+Number(c)+'?lang='+lang:weekly?(a==='weekly'?'/weekly':'/monthly')+'?lang='+lang+arPeriodQuery(b):'/rank?scope='+(b==='all'?'all':b==='week'?'week':'month')+arPeriodQuery(b);
    primary=arPageRead(path);primary.catch(()=>{});
  }
  try{if(a==='lab'&&!['model-test','server-guide'].includes(b)){
    const shop=!b?cmApi('GET','/pay/config').catch(()=>({})):null;
    const id=b&&/^\d+$/.test(b)?'&id='+encodeURIComponent(b):'';
    bootstrap=typeof cmLabBootstrap==='function'?await cmLabBootstrap(b?{id:+b,include:'health'}:{}):await cmApi('GET','/lab/bootstrap?include=health'+(!b?',sessions':'')+id);
    if(shop)bootstrap.shop=await shop;
    if(!alive())return;cm.me=bootstrap.user;cm.meChecked=true;ar.health=bootstrap.health||ar.health;
  }else if(a==='me'){
    bootstrap=await arMeOverview();if(!alive())return;ar.health=bootstrap.health||ar.health;
  }else if(primary){
    const health=Promise.resolve(ar.health||cmHealth());health.then(h=>{if(alive())ar.health=h;},()=>{});
    primary=await primary;version=primary.api_version||0;
    if(!version){const [,h]=await Promise.all([cmLoadMe(),health]);ar.health=h;}
  }else{const [,h]=await Promise.all([cmLoadMe(),ar.health||cmHealth()]);ar.health=h;}}
  catch(e){if(routeAlive()&&a==='me'&&e.status===401&&(!cmTok()||cmIdentityScope()===scope)){try{sessionStorage.setItem('hlCmBack','#/me');}catch(_){}location.hash='#/login';return;}if(alive())root.innerHTML=`<div class="cmnote">${esc(arErr(e))}</div>`;return;}
  if (!alive()) return;
  try {
    if (a === "login" || a === "signup") return arAuth(root, a);
    if (a === "oauth") return arOauthBack(root);
    if ((version || ar.health?.v || 0) < 4) { root.innerHTML = `<div class="cmnote">${arT().oldServer}</div>`; return; }
    if (a === "me") await arMe(root, alive,bootstrap);
    else if (a === "rank") await arRank(root, alive, b,primary);
    else if ((a === "monthly" || a === "weekly") && b === "p" && c) await arProblem(root, alive, +c,primary);
    else if ((a === "monthly" || a === "weekly") && b === "admin") await arAdmin(root, alive);
    else if (a === "lab" && b === "model-test") await arModelTest(root, alive);
    else if (a === "lab" && b === "server-guide") await arServerGuide(root, alive);
    else if (a === "lab") await (b ? arLabOne(root, alive, +b,bootstrap?.session) : arLabList(root, alive,bootstrap));
    else await arWeekly(root, alive, b,primary);
  } catch (e) { if (alive()) root.innerHTML = `<div class="cmnote">${esc(arErr(e))}</div>`; }
}

/* ── sign in / up: the community forms, on the site's own pages ── */
function arAuth(root, which) {
  if (cm.me) { cmBack(); return; }
  (which === "login" ? cmLogin : cmSignup)(root);
  for (const l of root.querySelectorAll("a[href='#/community/signup'],a[href='#/community/login']")) l.setAttribute("href", l.getAttribute("href").replace("/community", ""));
}

/* ── sign in with Google plus Kakao and NAVER (Korean pages) or GitHub and Discord (English pages) ── */
const OAUTH_BY_LANG = {ko: ["google", "kakao", "naver"], en: ["google", "github", "discord"]};
const arProvs = () => OAUTH_BY_LANG[lang === "en" ? "en" : "ko"];
const OAUTH_ICON = {
  google: '<svg viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.9 6.1C12.5 13.6 17.8 9.5 24 9.5z"/><path fill="#4285F4" d="M46.1 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.4c-.5 2.9-2.2 5.3-4.6 6.9l7.4 5.8c4.3-4 6.9-9.9 6.9-17.2z"/><path fill="#FBBC05" d="M10.6 28.6c-.5-1.4-.8-3-.8-4.6s.3-3.2.8-4.6l-7.9-6.1C1 16.6 0 20.2 0 24s1 7.4 2.7 10.7l7.9-6.1z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.4-5.8c-2.1 1.4-4.8 2.3-8.5 2.3-6.2 0-11.5-4.2-13.4-9.9l-7.9 6.1C6.6 42.6 14.6 48 24 48z"/></svg>',
  discord: '<svg viewBox="0 0 24 24"><path fill="#fff" d="M20.3 4.4A19.8 19.8 0 0 0 15.4 3l-.6 1.3a18.3 18.3 0 0 0-5.5 0L8.7 3a19.7 19.7 0 0 0-4.9 1.5C.7 9.1-.2 13.6.3 18.1a19.9 19.9 0 0 0 6 3l1.3-2.1a12.9 12.9 0 0 1-2-1l.5-.4a14.2 14.2 0 0 0 12.1 0l.5.4c-.6.4-1.3.7-2 1l1.3 2.1a19.8 19.8 0 0 0 6-3c.6-5.2-.8-9.7-3.7-13.7zM8 15.3c-1.2 0-2.2-1.1-2.2-2.4S6.8 10.5 8 10.5s2.2 1.1 2.2 2.4-1 2.4-2.2 2.4zm8 0c-1.2 0-2.2-1.1-2.2-2.4s1-2.4 2.2-2.4 2.2 1.1 2.2 2.4-1 2.4-2.2 2.4z"/></svg>',
  naver: '<svg viewBox="0 0 24 24"><path fill="#fff" d="M15.6 12.8 8.2 2H2v20h6.4V11.2L15.8 22H22V2h-6.4z"/></svg>',
  github: '<svg viewBox="0 0 24 24"><path fill="#fff" d="M12 .5a11.5 11.5 0 0 0-3.6 22.4c.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.2 1.2a11 11 0 0 1 5.8 0c2.2-1.5 3.2-1.2 3.2-1.2.6 1.6.2 2.8.1 3.1.8.8 1.2 1.9 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A11.5 11.5 0 0 0 12 .5z"/></svg>',
  kakao: '<svg viewBox="0 0 24 24"><path fill="#191919" d="M12 3C6.5 3 2 6.5 2 10.8c0 2.8 1.9 5.3 4.7 6.7l-1 3.6c-.1.3.3.6.6.4l4.2-2.8c.5.1 1 .1 1.5.1 5.5 0 10-3.5 10-7.9S17.5 3 12 3z"/></svg>'};
async function arHealth() { if (!ar.health || !ar.health.v) ar.health = await cmHealth(); return ar.health; }
function arOauthStart(p, ticket) {
  try { if (!sessionStorage.getItem("hlCmBack")) sessionStorage.setItem("hlCmBack", "#/"); } catch (e) {}
  location.href = cmBase() + "/api/oauth/" + p + "/start?return=" + encodeURIComponent(location.origin + location.pathname) + (ticket ? "&ticket=" + encodeURIComponent(ticket) : "");
}
/* the three buttons at the top of the sign-in and sign-up cards */
async function arOauth(root) {
  const card = root.querySelector(".cmauth .card"), form = card && card.querySelector("form"); if (!form) return;
  const h = await arHealth(), on = h.oauth || [], T = arT();
  const box = document.createElement("div"); box.className = "oauth";
  box.innerHTML = arProvs().map((p) => on.includes(p) ? `<a href="#" data-p="${p}" class="${p}">${OAUTH_ICON[p]}${T.oauthWith[p]}</a>`
    : `<span class="${p} off" title="${T.oauthOff}">${OAUTH_ICON[p]}${T.oauthWith[p]}</span>`).join("") + (arProvs().some((p) => on.includes(p)) ? "" : `<small>${T.oauthOff}</small>`);
  const or = document.createElement("div"); or.className = "oauth-or"; or.textContent = T.oauthOr;
  form.before(box, or);
  for (const a of box.querySelectorAll("a[data-p]")) a.onclick = (e) => { e.preventDefault(); arOauthStart(a.dataset.p); };
}
/* back from the provider: trade the one-time code for a session */
async function arOauthBack(root) {
  const T = arT(), q = new URLSearchParams(location.hash.split("?")[1] || "");
  history.replaceState(null, "", location.pathname + location.search + "#/oauth");
  if (q.get("e") || !q.get("c")) { root.innerHTML = `<div class="cmauth"><div class="card"><p class="cmerr">${esc(arErr({code: q.get("e") || "bad_code"}))}</p><a class="cmbtn pri" href="#/login">${T.login}</a></div></div>`; return; }
  try {
    const r = await cmApi("POST", "/oauth/redeem", {code: q.get("c")});
    cmTok(r.token); cm.me = r.user; cm.meChecked = true; arChip();
    if (q.get("linked")) { try { sessionStorage.removeItem("hlCmBack"); } catch (e) {} cmToast(T.linked); location.hash = "#/me"; return; }
    if (r.fresh) { try { sessionStorage.setItem("hlArNew", "1"); sessionStorage.removeItem("hlCmBack"); } catch (e) {} location.hash = "#/me"; return; }
    cmBack();
  } catch (e) { root.innerHTML = `<div class="cmauth"><div class="card"><p class="cmerr">${esc(arErr(e))}</p><a class="cmbtn pri" href="#/login">${T.login}</a></div></div>`; }
}

/* ── the month (legacy weekly links remain readable) ── */
async function arWeekly(root, alive, week,preloaded) {
  const T = arT(), q = arPeriodQuery(week);
  const j = preloaded||await cmApi("GET", "/monthly?lang=" + lang + q); if (!alive()) return;
  const period = arPeriodId(j), periods = j.months || j.weeks;
  const showArchive = periods?.length && (periods.length > 1 || periods.some(w => arPeriodId(w) !== period));
  let top = j.top ? {rows: j.top} : null;     // older servers leave the week's leaders out
  if (!top) { try { top = await cmApi("GET", "/rank?scope=month" + arPeriodQuery(period)); } catch (e) {} if (!alive()) return; }
  const P = j.problems, open = P.length && P[0].open, ends = P.length ? P[0].closes_at : 0, starts = P.length ? P[0].opens_at : 0;
  root.innerHTML = `
    <div class="cmtop"><div><h1>${T.weekH} <span class="arwk">${esc(arPeriodLabel(period))}</span></h1><p>${T.weekSub}</p></div>
      <div class="arwhen">${P.length ? `${arDate(starts)} – ${arDate(ends - 1)} · ${T.deadline} ${arDeadline(ends)}<br>${open ? `<b>${T.closesIn} ${arLeft(ends - j.now)}</b>` : T.closed}` : ""}</div></div>
    <div class="argrid"><div>
      ${P.length ? P.map((p) => `
        <a class="arcard" href="#/monthly/p/${p.id}">
          <div class="arno">${p.no}</div>
          <div class="arbody"><h3>${esc(p.title)}</h3>
            <div class="armeta"><span class="arkind ${p.kind}">${p.kind === "short" ? T.short : T.essay}</span><span>${esc(p.subject)}</span>
              ${arLevel(p.level)}<span>${p.points}${T.pts}</span>
              <span>${p.users} ${T.users} · ${p.solvers} ${T.solvers}</span></div></div>
          <div class="army">${p.best != null ? `<b>${p.best}</b><small>${T.best}</small>` : p.pending ? `<small>${T.pending}</small>` : `<span class="cmbtn sm pri">${T.solve}</span>`}</div>
        </a>`).join("") : `<div class="cmnote">${T.noProblems}</div>`}
      ${showArchive ? `<h3 class="arh3">${T.archive}</h3><div class="arweeks">${periods.map((w) => `<a href="#/monthly/${esc(arPeriodId(w))}" class="${arPeriodId(w) === period ? "on" : ""}">${esc(arPeriodLabel(w))}<small>${arDate(w.o)}–${arDate(w.c - 1)}</small></a>`).join("")}</div>` : ""}
    </div><aside class="arside">
      <div class="arpanel"><h3>${T.top}</h3>${top && top.rows.length ? `<ol class="ar-rank-top">${top.rows.slice(0, 8).map((r, i) => `<li><span class="ar-rank-position">${esc(r.rank ?? i + 1)}</span>${arRankPerson(r, true)}<span class="ar-rank-top-score"><b>${esc(r.total)}</b><small>${T.total}</small></span></li>`).join("")}</ol>` : `<p class="arempty">${T.empty}</p>`}
        <a class="cmbtn sm" href="#/rank/${esc(period)}">${T.rank} →</a></div>
      ${cm.me && cm.me.role === "admin" ? `<a class="cmbtn sm" href="#/monthly/admin">⚙ ${T.admin}</a>` : ""}
    </aside></div>`;
}

/* ── one problem ── */
function arResult(s, prob) {
  const T = arT(), d = s.detail || {};
  const S = arSheetT();
  if (s.status === "ai_suspected") return `<div class="cmnote"><b>${S.aiSuspected}</b><p>${S.aiReview}</p></div>`;
  if (s.status === "pending") return `<div class="cmnote">${T.pendingNote}</div>`;
  if (s.status === "error") return `<div class="cmnote">${T.errorNote}</div>`;
  const releaseAt = arMonthlyFeedbackRelease(s, prob);
  /* The API withholds private details too. This also hides stale, cached details if a
     monthly result was loaded before the correction-release deadline. */
  if (prob?.answerSheet && (s.feedback_held || (releaseAt && Date.now() / 1000 < releaseAt))) {
    return `<div class="arres ${s.score >= prob.points ? "ok" : ""}"><b>${T.score}</b><span>${s.score} / ${prob.points}${T.pts}</span></div><p class="arnote">${S.release(releaseAt ? arDeadline(releaseAt + 1) : "")}</p>`;
  }
  if (d.kind === "short") return `<div class="arres ${d.ok ? "ok" : "no"}"><b>${d.ok ? "✓ " + T.right : "✗ " + T.wrong}</b><span>${s.score} / ${prob.points}${T.pts}</span></div>`;
  return `<div class="arres ${s.score >= prob.points ? "ok" : ""}"><b>${T.score}</b><span>${s.score} / ${prob.points}${T.pts}</span>${d.grader ? `<small>${T.grader}: ${esc(d.grader)}</small>` : ""}</div>
    ${d.evidenceIssue ? `<p class="arwarn">${T.evidenceIssue}</p>` : ""}
    ${(d.scores || []).length ? `<table class="cmtbl artbl"><thead><tr><th style="width:42%">${T.criteria}</th><th style="width:70px">${T.score}</th><th>${T.evidence}</th></tr></thead><tbody>
      ${d.scores.map((c) => `<tr><td class="t"><b>${esc(c.id)}</b> ${esc(c.name)}<div class="arnote">${esc(c.note)}</div></td>
        <td><b>${c.got}</b>/${c.max}<div class="ardec ${c.decision}">${T[c.decision] || ""}</div></td>
        <td class="t">${(c.evidence || []).map((e) => `<q>${esc(e)}</q>`).join(" ")}</td></tr>`).join("")}</tbody></table>` : ""}
    ${(d.feedback || []).length ? `<h4 class="arh4">${T.feedback}</h4><ul class="arfb">${d.feedback.map((f) => `<li class="${f.kind}"><em>${f.kind === "good" ? T.good : T.fix}</em><q>${esc(f.quote)}</q> ${esc(f.note)}</li>`).join("")}</ul>` : ""}
    ${d.note ? `<p class="arnote">${esc(d.note)}</p>` : ""}`;
}
function arMonthlyFeedbackRelease(submission, problem) {
  const dates = [submission?.feedback_available_at, problem?.closes_at].map(Number).filter(value => Number.isFinite(value) && value > 0);
  return dates.length ? Math.max(...dates) : null;
}
let arScanner = null;
const arLoadScanner = () => arScanner || (arScanner = import("./sim/labscan/scanner.js?v=20261030-ocr").catch(error => { arScanner = null; throw error; }));
/* Weekly answers keep the same scanner and upload quality as exam photos. The student chooses
   which image to send; picking a file alone never starts a paid OCR request. */
function arBindAnswerPhoto(f, alive, T, onRead, options = {}) {
  const fi = f.querySelector("input[type=file]"), info = f.querySelector(".arinfo"), box = f.querySelector(".arshot");
  const authBase = cmBase(), authToken = cmTok();
  let photo = null, generation = 0, controller = null, disposed = false;
  const urls = new Set(), current = token => !disposed && alive() && token === generation && cmBase() === authBase && cmTok() === authToken;
  const imageUrl = blob => { const url = URL.createObjectURL(blob); urls.add(url); return url; };
  const note = (text, bad = false) => { info.hidden = false; info.textContent = text; info.className = "arinfo" + (bad ? " bad" : ""); };
  const clear = () => {
    generation++; controller?.abort(); controller = null; photo = null;
    for (const url of urls) URL.revokeObjectURL(url);
    urls.clear(); box.innerHTML = ""; box.hidden = true;
    options.onBusy?.(false);
  };
  const dispose = () => {
    if (disposed) return;
    clear(); disposed = true;
    window.removeEventListener("hashchange", dispose); window.removeEventListener("pagehide", dispose);
    if (ar.photoCleanup === dispose) ar.photoCleanup = null;
  };
  ar.photoCleanup = dispose;
  window.addEventListener("hashchange", dispose); window.addEventListener("pagehide", dispose);
  const paint = () => {
    if (!photo || disposed || !alive()) return;
    const selected = photo.clean && photo.selected === "clean" ? "clean" : "original", busy = photo.preparing || photo.reading;
    options.onBusy?.(!!busy);
    const warnings = [];
    if (photo.warning) warnings.push(photo.warning);
    if (selected === "clean" && photo.result?.autoScore < 0.75) warnings.push(T.scanWeak);
    if (photo.result?.quality?.focus != null && photo.result.quality.focus < 22) warnings.push(T.scanBlur);
    if (photo.result?.sourceShortSide && photo.result.sourceShortSide < 1000) warnings.push(T.scanSmall);
    box.hidden = false;
    box.innerHTML = `<div class="arq" style="margin:12px 0 8px;flex-wrap:wrap">
      <button type="button" class="cmbtn sm${selected === "original" ? " pri" : ""}" data-photo="original" aria-pressed="${selected === "original"}" ${busy ? "disabled" : ""}>${T.scanOriginal}</button>
      ${photo.clean ? `<button type="button" class="cmbtn sm${selected === "clean" ? " pri" : ""}" data-photo="clean" aria-pressed="${selected === "clean"}" ${busy ? "disabled" : ""}>${T.scanClean}</button>` : ""}</div>
      <img alt="${selected === "clean" ? T.scanClean : T.scanOriginal}" src="${selected === "clean" ? photo.cleanUrl : photo.originalUrl}">
      <p class="arnote" aria-live="polite">${esc(photo.preparing ? T.scanPreparing : photo.reading ? T.reading : T.scanCheck)}</p>
      ${warnings.map(text => `<p class="arinfo bad">${esc(text)}</p>`).join("")}
      <div class="arq" style="gap:8px;flex-wrap:wrap;margin:8px 0 14px">
        <button type="button" class="cmbtn sm pri" data-read-photo ${busy || photo.done ? "disabled" : ""}>${T.scanRead}</button>
        <button type="button" class="cmbtn sm" data-new-photo>${T.scanRetake}</button>
        <button type="button" class="cmbtn sm" data-cancel-photo>${T.scanCancel}</button></div>`;
    for (const button of box.querySelectorAll("[data-photo]")) button.onclick = () => { photo.selected = button.dataset.photo; paint(); };
    box.querySelector("[data-new-photo]").onclick = () => fi.click();
    box.querySelector("[data-cancel-photo]").onclick = () => { clear(); info.hidden = true; };
    box.querySelector("[data-read-photo]").onclick = read;
  };
  async function read() {
    if (!photo || photo.preparing || photo.reading || photo.done || options.blocked?.()) return;
    const token = generation, selected = photo.clean && photo.selected === "clean" ? photo.clean : photo.file, destination = options.target?.();
    const request = options.request?.(destination) || {path:"/ocr"};
    photo.reading = true; paint(); note(T.reading);
    const ctrl = new AbortController(); controller = ctrl;
    try {
      /* Preserve an already-small PNG/JPEG/WebP. Larger photos are encoded once through the
         shared 200dpi policy, with no repeated shrinking below the readable page size. */
      const scanner = await arLoadScanner(), blob = await scanner.encodeUpload(selected, { maxBytes: 4 * 1024 * 1024 }).catch(error => {
        if (error?.code === "image_too_big") throw { code: "ocr_image_too_big" };
        throw error;
      });
      if (!current(token)) return;
      const ext = { "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp" }[blob.type];
      if (!ext) throw { code: "bad_image" };
      const fd = new FormData(); fd.append("image", blob, `answer.${ext}`);
      if (request.original) {
        const original = selected === photo.file ? blob : await scanner.encodeUpload(photo.file, {maxBytes:4 * 1024 * 1024}).catch(error => {
          if (error?.code === "image_too_big") throw {code:"ocr_image_too_big"};
          throw error;
        });
        if (!current(token)) return;
        const originalExt = {"image/jpeg":"jpg","image/png":"png","image/webp":"webp"}[original.type];
        if (!originalExt) throw {code:"bad_image"};
        fd.append("original_image",original,`original.${originalExt}`);
      }
      for (const [name,value] of Object.entries(request.fields || {})) fd.append(name,String(value));
      const response = await fetch(authBase + "/api" + request.path + "?mode=" + (f.math.checked ? "math" : "text"), {
        method: "POST", headers: { Authorization: "Bearer " + authToken }, body: fd, signal: ctrl.signal,
      });
      const result = await response.json().catch(() => ({ error: "server_error" }));
      if (!current(token)) return;
      if (!response.ok) throw { code: result.error };
      if (typeof result.text !== "string" || !result.text.trim()) throw { code: "ocr_empty" };
      onRead(result.text, destination, result); photo.done = true;
      const ta = destination || f.querySelector("textarea");
      note(ta.value.length > ta.maxLength && ta.maxLength > 0 ? T.scanLong : T.readDone);
      info.className = "arinfo ok"; ta.focus();
    } catch (error) {
      if (current(token)) note(arErr(error), true);
    } finally {
      if (controller === ctrl) controller = null;
      if (current(token)) { photo.reading = false; paint(); }
      else if (cmBase() !== authBase || cmTok() !== authToken) dispose();
    }
  }
  fi.onchange = async () => {
    const file = fi.files[0]; fi.value = ""; if (!file) return;
    clear(); info.hidden = true;
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) { note(T.err.bad_image, true); return; }
    const token = generation;
    photo = { file, originalUrl: imageUrl(file), selected: "original", preparing: true }; paint();
    try {
      const scanner = await arLoadScanner(); if (!current(token)) return;
      if (!scanner.canProcess()) { photo.warning = T.scanUnavailable; return; }
      const result = await scanner.processShot(file, { mode: "clean" });
      if (!current(token)) return;
      photo.result = result; photo.clean = result.blob; photo.cleanUrl = imageUrl(result.blob); photo.selected = "clean";
    } catch (error) {
      if (current(token)) photo.warning = T.scanFailed;
    } finally {
      if (current(token)) { photo.preparing = false; paint(); }
    }
  };
}

/* Monthly answer sheets mirror the printable, labelled answer/working boxes. The server
   validates these canonical part ids and owns the three-attempt limit. */
function arSheetT() {
  return lang === "ko" ? {
    h: "답안지", print: "답안지 양식 열기 · 인쇄", help: "소문항마다 최종 답과 풀이를 함께 작성하세요. 수식은 LaTeX로 입력할 수 있습니다. 풀지 않은 소문항은 두 칸을 모두 비워도 됩니다.",
    answer: "최종 답", answerHint: "LaTeX 예: \\omega(q)=\\sqrt{...} · 일반 글도 입력할 수 있습니다.", working: "풀이·근거", workingHint: "유도 과정과 근거를 적으세요. 수식은 $...$ 또는 $$...$$로 입력합니다.",
    typed: "직접 입력", photo: "답안지 사진 읽기", photoHelp: "답안지 양식에서 소문항별로 작성한 부분을 찍어 올리세요. 읽은 풀이를 확인하고 최종 답도 채운 뒤 제출하세요. 여러 사진은 같은 소문항 풀이에 이어 붙일 수 있습니다.",
    photoPart: "사진을 넣을 소문항", preview: "수식 미리보기", submit: "답안 제출 · 기회 1회 사용", total: "문제당 제출 기회 3회", remaining: n => `남은 제출 기회 ${n} / 3회`,
    saved: "작성 내용은 이 계정의 브라우저에 임시 저장됩니다. 임시 저장과 사진 읽기는 제출 기회를 사용하지 않습니다.", exhausted: "이 문제의 제출 기회 3회를 모두 사용했습니다. 기존 채점 결과는 아래에서 확인할 수 있습니다.",
    incomplete: id => `${id}: 최종 답과 풀이를 함께 입력하세요.`, empty: "한 소문항 이상에 최종 답과 풀이를 입력하세요.", tooLong: "답안이 너무 깁니다. 전체 답과 풀이를 60,000자 이내로 줄여주세요.", partLong: id => `${id}: 최종 답은 4,000자, 풀이는 16,000자 이내로 줄여주세요.`, photoLong: "읽은 풀이가 소문항당 16,000자를 넘었습니다. 내용을 확인하고 줄인 뒤 제출하세요.",
    processing: "이 답안은 이미 접수되어 채점 중입니다. 같은 답안을 다시 제출해도 기회가 추가로 사용되지 않습니다.", conflict: "이미 접수된 제출 번호입니다. 답안을 수정한 뒤 다시 제출하세요.", next: "답안을 수정하면 남은 기회로 다시 제출할 수 있습니다.",
    used: "제출이 접수되면 기회 1회가 사용됩니다. 통신 오류로 같은 제출을 다시 전송해도 중복 차감되지 않습니다.",
    release: date => `제출 직후에는 총점만 표시됩니다. 소문항별 채점 내역과 첨삭은 마감 후${date ? ` ${date}부터` : ""} 공개됩니다.`,
    authorship: "직접 입력한 답안은 AI 작성 의심 여부를 확인합니다. AI 판별은 오판할 수 있으며, 의심 답안은 제출 기회 1회를 사용하고 채점하지 않습니다. 본인이 직접 푼 손글씨 답안 제출을 권장합니다. 손글씨 사진만으로 작성자를 확인할 수는 없습니다.",
    retained: "제출한 월별 문제 답안과 업로드한 답안 사진은 서버에 보관됩니다.",
    aiSuspected: "AI 작성 의심으로 채점 보류 · 제출 기회 1회 사용",
    aiReview: "AI 판별에는 오판 가능성이 있습니다. 오판이 의심되면 관리자에게 검토를 요청해 주세요.",
    photoReadDone: "사진을 읽고 촬영 원본을 서버에 보관했습니다. 읽은 풀이가 답안과 같은지 확인하고 최종 답도 채운 뒤 제출하세요.",
    originalPhoto: "제출한 촬영 원본 보기", photoFailed: "답안 사진을 불러오지 못했습니다. 다시 시도해 주세요.",
    grading: "답안을 확인하고 채점하는 중입니다. 최대 2분 정도 걸릴 수 있습니다."
  } : {
    h: "Answer sheet", print: "Open / print the answer sheet", help: "Enter the final answer and supporting work for each part. LaTeX is supported. Leave both boxes blank for any part you do not attempt.",
    answer: "Final answer", answerHint: "LaTeX, e.g. \\omega(q)=\\sqrt{...}, or ordinary text.", working: "Working and justification", workingHint: "Show your derivation and reasoning. Use $...$ or $$...$$ for formulas.",
    typed: "Type answers", photo: "Read answer-sheet photos", photoHelp: "Photograph a labelled part of the provided answer sheet. Check the recognized working and complete its final-answer box before submitting. Further photos append to the selected part.",
    photoPart: "Part shown in the photo", preview: "Formula preview", submit: "Submit answer · use 1 attempt", total: "3 submission attempts per problem", remaining: n => `${n} / 3 attempts remaining`,
    saved: "Drafts are saved for this account in this browser. Saving a draft or reading a photo does not use an attempt.", exhausted: "All 3 attempts for this problem have been used. Your existing grades remain below.",
    incomplete: id => `${id}: enter both a final answer and supporting work.`, empty: "Complete the final answer and working for at least one part.", tooLong: "Keep all answers and working within 60,000 characters.", partLong: id => `${id}: keep the answer within 4,000 characters and the working within 16,000.`, photoLong: "The recognized working exceeds 16,000 characters for this part. Check and shorten it before submitting.",
    processing: "This answer has already been accepted and is being graded. Retrying it does not use another attempt.", conflict: "This submission identifier has already been used. Edit your answer before submitting again.", next: "Edit your answer to submit again using a remaining attempt.",
    used: "An accepted submission uses one attempt. Resending the same submission after a network error does not use an additional attempt.",
    release: date => `Only the total score is shown immediately. Per-part marks and corrections are released after the deadline${date ? `, from ${date}` : ""}.`,
    authorship: "Typed answers are screened for suspected AI writing. This can produce false positives. A flagged answer uses one attempt and is not graded. We recommend submitting your own handwritten solution. A handwriting photo alone does not establish authorship.",
    retained: "Submitted monthly answers and uploaded answer photos are stored on the server.",
    aiSuspected: "Suspected AI writing · not graded · 1 attempt used",
    aiReview: "AI screening can produce false positives. If you believe this was a mistake, ask an administrator to review it.",
    photoReadDone: "The photo has been read and its capture saved on the server. Check the recognized working and complete the final answer before submitting.",
    originalPhoto: "View submitted capture", photoFailed: "The answer photo could not be loaded. Please try again.",
    grading: "Checking and grading your answer. This may take about 2 minutes."
  };
}
function arSheetPartLabel(part) { const label = (lang === "en" ? part.label_en : part.label_ko); return label ? `${part.id.includes(".") ? part.id : "("+part.id+")"} ${label}` : part.id; }
function arSheetFinalPreview(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  return /\$/.test(text) || !/[\\_^{}=]|^[\d+−-]/.test(text) ? arSheetWorkingPreview(text) : `<div>$$${esc(text)}$$</div>`;
}
function arSheetWorkingPreview(value) {
  return String(value || "").split(/(\$\$[\s\S]*?\$\$)/).map(part => part.startsWith("$$") && part.endsWith("$$") ? `<div>${esc(part)}</div>` : arText(part)).join("");
}
function arSheetDraftKey(p) {
  const account = cm.me?.id != null ? "id:"+cm.me.id : cm.me?.username ? "legacy:"+cm.me.username : null;
  return account == null ? null : `hlMonthlySheet:${encodeURIComponent(typeof cmBase === "function" ? cmBase() : "")}:${encodeURIComponent(account)}:${p.id}:${p.answerSheet.version}`;
}
function arSheetParts(p, form) {
  const S = arSheetT();
  const parts = p.answerSheet.parts.map(part => ({id:part.id,
    answer:form.querySelector(`[data-sheet-answer="${part.id}"]`).value.trim(),
    working:form.querySelector(`[data-sheet-working="${part.id}"]`).value.trim()}));
  for (const part of parts) if (!!part.answer !== !!part.working) throw {sheetMessage:S.incomplete(part.id)};
  for (const part of parts) if (part.answer.length > 4000 || part.working.length > 16000) throw {sheetMessage:S.partLong(part.id)};
  if (!parts.some(part => part.answer)) throw {sheetMessage:S.empty};
  if (parts.reduce((n, part) => n + part.answer.length + part.working.length, 0) > 60000) throw {sheetMessage:S.tooLong};
  return parts;
}
function arSheetError(error) {
  const S = arSheetT();
  return error?.sheetMessage || ({attempts_exhausted:S.exhausted, incomplete_part:S.empty, bad_answer_sheet:S.empty,
    bad_answer:S.empty, request_conflict:S.conflict}[error?.code]) || arErr(error);
}
function arMonthlyAnswerHtml(p, ocrOn) {
  const T = arT(), S = arSheetT(), signed = !!cm.me, attempts = p.attempts, exhausted = attempts?.remaining === 0;
  return `<h3>${S.h}</h3><div class="arsheet-top"><a class="cmbtn sm" href="sim/monthly-answer-sheet.html?id=${p.id}&lang=${lang}" target="_blank" rel="noopener">${S.print} ↗</a>
      <b class="artries" id="arSheetAttempts">${Number.isInteger(attempts?.remaining) ? S.remaining(attempts.remaining) : S.total}</b></div>
    <p class="arnote">${S.help}</p><p class="arnote">${S.used}</p>
    <p class="arnote">${S.release(p.closes_at ? arDeadline(p.closes_at + 1) : "")}</p><p class="arnote">${S.authorship}</p><p class="arnote">${S.retained}</p>
    ${!signed ? `<p>${T.loginToSubmit} <a class="cmbtn sm pri" href="#/login" id="arLogin">${T.login}</a></p>` : ""}
    ${exhausted ? `<p class="cmnote">${S.exhausted}</p>` : ""}
    <form id="arSheetF" class="armonthly-sheet">
      <div class="arsheet-modes" role="group" aria-label="${S.h}"><button type="button" class="cmbtn sm pri" data-sheet-mode="typed" aria-pressed="true">${S.typed}</button><button type="button" class="cmbtn sm" data-sheet-mode="photo" aria-pressed="false">${S.photo}</button></div>
      <div class="arsheet-photo" hidden>
        <p class="arnote">${S.photoHelp}</p>
        <label class="arsheet-select">${S.photoPart}<select name="photo_part" ${!signed || exhausted ? "disabled" : ""}>${p.answerSheet.parts.map(part => `<option value="${esc(part.id)}">${esc(arSheetPartLabel(part))}</option>`).join("")}</select></label>
        <div class="arocr"><label class="cmbtn sm ${!signed || !ocrOn || exhausted ? "dis" : ""}">📷 ${T.photo}<input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" hidden ${!signed || !ocrOn || exhausted ? "disabled" : ""}></label>
          <label class="archk"><input type="checkbox" name="math" checked ${!signed || exhausted ? "disabled" : ""}> ${T.mathMode}</label>
          <small>${ocrOn ? "" : T.ocrOff}</small></div><div class="arshot" hidden></div><p class="arinfo" hidden></p>
      </div>
      ${p.answerSheet.parts.map(part => `<fieldset class="aranswer-part" data-sheet-part="${esc(part.id)}" ${!signed || exhausted ? "disabled" : ""}>
        <legend>${esc(arSheetPartLabel(part))}<span>${part.points}${T.pts}</span></legend>
        <label>${S.answer}<textarea data-sheet-answer="${esc(part.id)}" rows="2" maxlength="4000" placeholder="${esc(S.answerHint)}"></textarea></label>
        <div class="arsheet-preview" data-sheet-answer-preview="${esc(part.id)}" aria-label="${S.preview}"></div>
        <label>${S.working}<textarea data-sheet-working="${esc(part.id)}" rows="6" maxlength="16000" placeholder="${esc(S.workingHint)}"></textarea></label>
        <div class="arsheet-preview" data-sheet-working-preview="${esc(part.id)}" aria-label="${S.preview}"></div>
      </fieldset>`).join("")}
      ${signed ? `<p class="arnote">${S.saved}</p>` : ""}<button class="cmbtn pri" type="submit" ${!signed || exhausted ? "disabled" : ""}>${S.submit}</button>
    </form>`;
}
function arMonthlySavedAnswer(submission) {
  const sheet = submission.answer_sheet, S = arSheetT();
  const photos = (submission.photo_attachments || []).map(photo => `<div class="arsheet-photo-saved"><button class="cmbtn sm" type="button" data-monthly-photo="${esc(photo.id)}">${S.originalPhoto} · ${esc(photo.part_id)}</button><p class="arinfo" hidden></p><img class="armonthly-original" alt="${S.originalPhoto} · ${esc(photo.part_id)}" hidden style="max-width:100%;height:auto"></div>`).join("");
  if (!sheet?.parts) return `<pre class="aranswer">${esc(submission.answer)}</pre>`+photos;
  return `<div class="arsheet-saved">${sheet.parts.filter(part => part.answer || part.working).map(part => `<section><h4>${esc(part.id)}</h4><b>${S.answer}</b><div>${arSheetFinalPreview(part.answer)}</div><b>${S.working}</b><div>${arSheetWorkingPreview(part.working)}</div></section>`).join("")}${photos}</div>`;
}
function arBindMonthlyPhotos(root, alive) {
  const buttons = [...(root.querySelectorAll?.("[data-monthly-photo]") || [])];
  if (!buttons.length || !cm.me) return;
  ar.monthlyPhotoCleanup?.();
  const S = arSheetT(), base = cmBase(), token = cmTok(), owner = cm.me.id ?? cm.me.username, urls = new Set(), controllers = new Set();
  let disposed = false;
  const current = () => !disposed && alive() && cmBase() === base && cmTok() === token && !!cm.me && (cm.me.id ?? cm.me.username) === owner;
  const dispose = () => {
    if (disposed) return; disposed = true;
    for (const controller of controllers) controller.abort(); controllers.clear();
    for (const url of urls) URL.revokeObjectURL(url); urls.clear();
    for (const button of buttons) { const image = button.parentElement.querySelector("img"); image.removeAttribute("src"); image.hidden = true; }
    window.removeEventListener("hashchange",dispose); window.removeEventListener("pagehide",dispose);
    if (ar.monthlyPhotoCleanup === dispose) ar.monthlyPhotoCleanup = null;
  };
  ar.monthlyPhotoCleanup = dispose;
  window.addEventListener("hashchange",dispose); window.addEventListener("pagehide",dispose);
  for (const button of buttons) button.onclick = async () => {
    if (!current()) { dispose(); return; }
    const box = button.parentElement, image = box.querySelector("img"), info = box.querySelector(".arinfo"), controller = new AbortController();
    controllers.add(controller); button.disabled = true; info.hidden = true;
    try {
      const response = await fetch(base+"/api/monthly/photos/"+encodeURIComponent(button.dataset.monthlyPhoto),{headers:{Authorization:"Bearer "+token},signal:controller.signal});
      if (!response.ok) throw new Error("photo_unavailable");
      const blob = await response.blob();
      if (!current()) { dispose(); return; }
      if (!/^image\/(jpeg|png|webp)$/.test(blob.type)) throw new Error("bad_image");
      const url = URL.createObjectURL(blob); urls.add(url); image.src = url; image.hidden = false; button.hidden = true;
    } catch (error) {
      if (current()) { info.textContent = S.photoFailed; info.hidden = false; info.className = "arinfo bad"; }
    } finally { controllers.delete(controller); if (current()) button.disabled = false; else dispose(); }
  };
}
function arBindMonthlyAnswer(root, p, alive, ocrOn) {
  const pageAlive = alive, owner = cm.me?.id ?? cm.me?.username, base = cmBase(), token = typeof cmTok === "function" ? cmTok() : null;
  alive = () => pageAlive() && (cm.me?.id ?? cm.me?.username) === owner && cmBase() === base && (typeof cmTok !== "function" || cmTok() === token);
  const f = root.querySelector("#arSheetF"), out = root.querySelector("#arOut"), S = arSheetT(), T = arT();
  const button = f.querySelector("button[type=submit]"), key = arSheetDraftKey(p), fields = [...f.querySelectorAll("[data-sheet-answer], [data-sheet-working]")];
  let requestId = null, accepted = false, viaOcr = false, busy = false, photoBusy = false, previewTimer = null;
  const photos = new Map();
  const attempts = () => p.attempts?.remaining !== 0;
  const save = () => { if (!key || !alive()) return; try { localStorage.setItem(key, JSON.stringify({version:p.answerSheet.version,request_id:requestId,accepted,via_ocr:viaOcr,photos:[...photos].map(([id,part_id])=>({id,part_id})),
    parts:p.answerSheet.parts.map(part => ({id:part.id, answer:f.querySelector(`[data-sheet-answer="${part.id}"]`).value,working:f.querySelector(`[data-sheet-working="${part.id}"]`).value}))})); } catch (_) {} };
  const preview = () => {
    for (const part of p.answerSheet.parts) {
      f.querySelector(`[data-sheet-answer-preview="${part.id}"]`).innerHTML = arSheetFinalPreview(f.querySelector(`[data-sheet-answer="${part.id}"]`).value);
      f.querySelector(`[data-sheet-working-preview="${part.id}"]`).innerHTML = arSheetWorkingPreview(f.querySelector(`[data-sheet-working="${part.id}"]`).value);
    }
    arMath(f);
  };
  if (key) try {
    const draft = JSON.parse(localStorage.getItem(key) || "null");
    if (draft?.version === p.answerSheet.version && Array.isArray(draft.parts)) {
      for (const part of p.answerSheet.parts) { const saved = draft.parts.find(x => x.id === part.id); if (!saved) continue;
        f.querySelector(`[data-sheet-answer="${part.id}"]`).value = typeof saved.answer === "string" ? saved.answer.slice(0,4000) : "";
        f.querySelector(`[data-sheet-working="${part.id}"]`).value = typeof saved.working === "string" ? saved.working.slice(0,16000) : ""; }
      requestId = typeof draft.request_id === "string" ? draft.request_id : null; accepted = !!draft.accepted; viaOcr = !!draft.via_ocr;
      for (const photo of draft.photos || []) if (typeof photo.id === "string" && photo.id.length <= 100 && p.answerSheet.parts.some(part=>part.id === photo.part_id)) photos.set(photo.id,photo.part_id);
    }
  } catch (_) {}
  button.disabled = !cm.me || !attempts() || accepted;
  if (accepted && attempts()) out.innerHTML = `<p class="arnote">${S.next}</p>`;
  const edited = () => { if (busy || !alive()) return; requestId = null; accepted = false; button.disabled = !cm.me || !attempts() || photoBusy; save(); clearTimeout(previewTimer); previewTimer = setTimeout(preview,250); };
  for (const field of fields) field.oninput = edited;
  preview();
  for (const mode of f.querySelectorAll("[data-sheet-mode]")) mode.onclick = () => {
    const photo = mode.dataset.sheetMode === "photo"; f.querySelector(".arsheet-photo").hidden = !photo;
    for (const item of f.querySelectorAll("[data-sheet-mode]")) { const on = item === mode; item.classList.toggle("pri",on); item.setAttribute("aria-pressed",String(on)); }
  };
  if (cm.me && ocrOn && attempts()) arBindAnswerPhoto(f,alive,{...T,scanLong:S.photoLong,readDone:S.photoReadDone},(text,destination,result) => {
    if (!destination) return; destination.value = (destination.value.trim() ? destination.value.trim()+"\n\n" : "")+text;
    if (typeof result?.photo_id === "string" && result.part_id === destination.dataset.sheetWorking) photos.set(result.photo_id,result.part_id);
    viaOcr = true; edited(); preview();
  }, {target:() => f.querySelector(`[data-sheet-working="${f.photo_part.value}"]`), blocked:() => busy || !attempts(),
    request:destination => ({path:`/monthly/problems/${p.id}/photos`,fields:{part_id:destination.dataset.sheetWorking},original:true}),
    onBusy: value => { photoBusy = value; if (alive()) button.disabled = !cm.me || !attempts() || accepted || busy || photoBusy; }});
  f.onsubmit = async event => {
    event.preventDefault(); if (busy || photoBusy || !cm.me || !attempts() || accepted || !alive()) return;
    let parts; try { parts = arSheetParts(p,f); } catch (error) { out.innerHTML = `<p class="arinfo bad">${esc(arSheetError(error))}</p>`; return; }
    if (!requestId) requestId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "monthly-"+Date.now().toString(36)+"-"+Math.random().toString(36).slice(2);
    save(); busy = true; button.disabled = true;
    for (const field of fields) field.disabled = true;
    for (const control of f.querySelectorAll("input[type=file],select[name=photo_part],input[name=math]")) control.disabled = true;
    out.innerHTML = `<p class="arinfo">${S.grading}</p>`;
    try {
      const photoIds = [...photos].filter(([,partId])=>parts.some(part=>part.id === partId && part.answer && part.working)).map(([id])=>id);
      const result = await cmApi("POST",`/problems/${p.id}/submit`,{parts,request_id:requestId,sheet_version:p.answerSheet.version,photo_ids:photoIds,via_ocr:viaOcr,lang});
      if (!alive()) return;
      if (result.attempts) { p.attempts = result.attempts; root.querySelector("#arSheetAttempts").textContent = S.remaining(result.attempts.remaining); }
      accepted = !result.processing; save();
      out.innerHTML = result.processing ? `<p class="arinfo">${S.processing}</p>` : `<h4 class="arh4">${T.result}</h4>`+arResult(result,p)+`<p class="arnote">${attempts() ? S.next : S.exhausted}</p>`; arMath(out);
    } catch (error) {
      if (!alive()) return;
      if (error?.code === "attempts_exhausted") { p.attempts = {limit:3,used:3,remaining:0}; root.querySelector("#arSheetAttempts").textContent=S.remaining(0); }
      out.innerHTML = `<p class="arinfo bad">${esc(arSheetError(error))}</p>`;
    } finally {
      busy = false; if (alive()) { for (const field of fields) field.disabled = !attempts();
        for (const control of f.querySelectorAll("input[type=file],select[name=photo_part],input[name=math]")) control.disabled = !attempts() || (control.type === "file" && !ocrOn);
        button.disabled = !attempts() || accepted || photoBusy; }
    }
  };
}
async function arProblem(root, alive, id,preloaded) {
  ar.photoCleanup?.();
  ar.monthlyPhotoCleanup?.();
  const T = arT(), j = preloaded||await cmApi("GET", `/problems/${id}?lang=${lang}`); if (!alive()) return;
  const p = j.problem, now = Math.floor(Date.now() / 1000), ocrOn = j.health && j.health.ocr;
  root.innerHTML = `
    <div class="arcrumb"><a href="#/monthly/${esc(arPeriodId(p))}">← ${T.weekH} ${esc(arPeriodLabel(p))}</a></div>
    <div class="arprob">
      <div class="arph"><span class="arno">${p.no}</span><div><h1>${esc(p.title)}</h1>
        <div class="armeta"><span class="arkind ${p.kind}">${p.kind === "short" ? T.short : T.essay}</span><span>${esc(p.subject)}</span>${arLevel(p.level)}<span>${esc(tierName(p.level))}</span>
          <span>${p.points}${T.pts}</span><span>${T.deadline} ${arDeadline(p.closes_at)}</span><span>${p.open ? `${T.closesIn} ${arLeft(p.closes_at - now)}` : T.closed}</span>${p.source && !p.answerSheet ? `<span>${esc(p.source)}</span>` : ""}</div></div></div>
      <div class="arstmt" id="arStmt">${arPublishedText(p.body)}</div>
      ${p.criteria ? `<div class="arcrit">${p.criteria.map((c) => `<span><b>${esc(c.id)}</b> ${esc(c.name)} · ${c.max}${T.pts}</span>`).join("")}</div>` : ""}
    </div>
    <div class="arpanel" id="arAns">
      ${p.answerSheet?.parts?.length ? arMonthlyAnswerHtml(p,ocrOn) : `<h3>${T.answer}</h3>
      ${!cm.me ? `<p class="arempty">${T.loginToSubmit}</p><a class="cmbtn pri" href="#/login" id="arLogin">${T.login}</a>` : p.kind === "short" ? `
        <form id="arF" class="arshort"><input name="a" inputmode="decimal" autocomplete="off" placeholder="${T.answerPh}" maxlength="60">${p.unit ? `<span>${esc(p.unit)}</span>` : ""}
          <button class="cmbtn pri" type="submit">${T.submit}</button></form>` : `
        <form id="arF" class="aressay">
          <div class="arocr">
            <label class="cmbtn sm ${ocrOn ? "" : "dis"}">📷 ${T.photo}<input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" hidden ${ocrOn ? "" : "disabled"}></label>
            <label class="archk"><input type="checkbox" name="math" checked> ${T.mathMode}</label>
            <small>${ocrOn ? T.photoHint : T.ocrOff}</small>
          </div>
          <div class="arshot" hidden><img alt=""></div>
          <p class="arinfo" hidden></p>
          <textarea name="a" rows="12" maxlength="12000" placeholder="${T.essayPh}"></textarea>
          <div class="arprevh">${T.preview}</div><div class="arprev" id="arPrev"></div>
          <button class="cmbtn pri" type="submit">${T.submit}</button></form>`}`}
      <div id="arOut"></div>
    </div>
    ${p.mine && p.mine.length ? `<div class="arpanel"><h3>${T.mine}</h3>${p.mine.map((s) => `
      <details class="arsub"><summary><b>${s.status === "graded" ? s.score + " / " + p.points : T[s.status] || s.status}</b>
        <span>${cmFull(s.created_at)}</span>${s.via_ocr ? `<small>${T.viaOcr}</small>` : ""}${s.in_week ? "" : `<small>${T.practice}</small>`}</summary>
        ${arMonthlySavedAnswer(s)}${arResult(s, p)}</details>`).join("")}</div>` : ""}
    <div class="arpanel"><h3>${T.solution}</h3>${p.solution ? `<div class="arstmt" id="arSol">${arPublishedText(p.solution)}</div>` : `<p class="arempty">${T.solutionLater}</p>`}</div>`;
  arMath(root);
  arBindMonthlyPhotos(root,alive);
  const lg = root.querySelector("#arLogin"); if (lg) lg.onclick = () => { try { sessionStorage.setItem("hlCmBack", location.hash); } catch (e) {} };
  if (p.answerSheet?.parts?.length) { arBindMonthlyAnswer(root,p,alive,ocrOn); return; }
  const f = root.querySelector("#arF"); if (!f) return;
  const out = root.querySelector("#arOut"); let viaOcr = false;
  const ta = f.querySelector("textarea");
  if (ta) {
    const key = "hlArDraft" + id; try { ta.value = localStorage.getItem(key) || ""; } catch (e) {}
    const prev = root.querySelector("#arPrev"); let tm = 0;
    const upd = () => { prev.innerHTML = arText(ta.value); arMath(prev); try { localStorage.setItem(key, ta.value); } catch (e) {} };
    ta.oninput = () => { clearTimeout(tm); tm = setTimeout(upd, 350); }; upd();
    arBindAnswerPhoto(f, alive, T, text => { ta.value = (ta.value.trim() ? ta.value.trim() + "\n\n" : "") + text; viaOcr = true; upd(); });
  }
  f.onsubmit = async (e) => {
    e.preventDefault(); const btn = f.querySelector("button[type=submit]"); btn.disabled = true;
    out.innerHTML = `<p class="arinfo">${T.grading}</p>`;
    try {
      const r = await cmApi("POST", `/problems/${id}/submit`, {answer: f.a.value, via_ocr: viaOcr, lang});
      out.innerHTML = `<h4 class="arh4">${T.result}</h4>` + arResult(r, p); arMath(out);
      if (ta && r.status === "graded") try { localStorage.removeItem("hlArDraft" + id); } catch (e) {}
      setTimeout(() => { if (alive()) arProblem(root, alive, id).then(() => { const o = root.querySelector("#arOut"); if (o) { o.innerHTML = `<h4 class="arh4">${T.result}</h4>` + arResult(r, p); o.scrollIntoView({block: "nearest"}); } }); }, 50);
    } catch (er) { out.innerHTML = `<p class="arinfo bad">${esc(arErr(er))}</p>`; btn.disabled = false; }
  };
}

/* ── rankings ── */
function arRankPerson(row, compact = false) {
  const T = arT(), nickname = String(row.nickname || ""), avatar = row.av || row.avatar;
  const picture = avatar && /^[A-Za-z0-9_-]{8,32}$/.test(avatar) ? cmAv(nickname, "ar-rank-avatar", avatar) :
    `<span class="cmav ar-rank-avatar ar-rank-avatar-default" aria-hidden="true"><svg viewBox="0 0 32 32" focusable="false"><circle cx="16" cy="11" r="5"/><path d="M6 28v-3a10 10 0 0 1 20 0v3z"/></svg></span>`;
  return `<a class="ar-rank-person" href="${esc(cmProfileHref(nickname))}" title="${esc(nickname)} · ${lang === "en" ? "View public profile" : "공개 프로필 보기"}">${picture}<span class="ar-rank-identity"><span class="ar-rank-name">${esc(nickname)}</span><span class="ar-rank-meta${compact ? "" : " ar-rank-mobile-meta"}">${arTier(row.lv)}${compact ? "" : `<span>${esc(row.solved)} ${T.solvedN}</span>`}</span></span></a>`;
}
async function arRank(root, alive, which,preloaded) {
  const T = arT(), scope = which === "all" ? "all" : "month";
  const j = preloaded||await cmApi("GET", "/rank?scope=" + scope + arPeriodQuery(which)); if (!alive()) return;
  const period = arPeriodId(j);
  root.innerHTML = `
    <div class="cmtop"><div><h1>${T.rankH}${period ? ` <span class="arwk">${esc(arPeriodLabel(period))}</span>` : ""}</h1><p>${T.rankSub}</p></div>
      <div class="cmseg"><a href="#/rank/month" class="${scope === "month" ? "on" : ""}">${T.rankWeek}</a><a href="#/rank/all" class="${scope === "all" ? "on" : ""}">${T.rankAll}</a></div></div>
    <div class="arpanel ar-rank-panel">${j.rows.length ? `<table class="ar-rank-table"><caption>${T.rankH} · ${scope === "all" ? T.rankAll : esc(arPeriodLabel(period))}</caption><thead><tr><th scope="col" class="ar-rank-number">#</th><th scope="col" class="ar-rank-user">${T.nick}</th><th scope="col" class="ar-rank-tier">${T.tier}</th>
      <th scope="col" class="ar-rank-score">${scope === "all" ? T.rating : T.total}</th><th scope="col" class="ar-rank-solved-cell">${T.solved}</th></tr></thead>
      <tbody>${j.rows.map((r) => `<tr class="${cm.me && r.nickname === cm.me.nickname ? "armine" : ""}"><td class="ar-rank-number"><b class="ar-rank-position">${esc(r.rank)}</b></td><td class="ar-rank-user">${arRankPerson(r)}</td>
        <td class="ar-rank-tier">${arTier(r.lv)}</td><td class="ar-rank-score"><b>${esc(scope === "all" ? (r.rating ?? r.total) : r.total)}</b></td><td class="ar-rank-solved-cell">${esc(r.solved)}</td></tr>`).join("")}</tbody></table>`
      : `<p class="arempty">${T.empty}</p>`}</div>
    <p class="arfoot">${T.ratingHelp}</p>`;
}

/* ── my record ── */
async function arMe(root, alive,overview) {
  const T = arT();
  if (!cm.me) { try { sessionStorage.setItem("hlCmBack", "#/me"); } catch (e) {} location.hash = "#/login"; return; }
  overview=overview||await arMeOverview();if(!alive())return;
  const j = overview.stats;
  j.lv = j.lv || 0; j.rating = j.rating || 0;               // a server from before the rating sends neither
  root.innerHTML = `
    <div class="cmtop"><div><h1>${cmAv(cm.me.nickname, "", cm.me.avatar)} ${esc(cm.me.nickname)} ${arTier(j.lv)}</h1><p>@${esc(cm.me.username)}</p></div>
      <div style="display:flex;gap:6px"><a class="cmbtn sm" href="#/community/account">${T.settings}</a><button class="cmbtn sm" id="arLogout">${T.logout}</button></div></div>
    ${arModelTestLink()}
    <div class="arstats"><div><small>${T.rating}</small><b style="color:${TIER_COL[tierKey(j.lv)]}">${j.rating}</b></div><div><small>${T.myRank}</small><b>${j.rank || "–"}</b></div><div><small>${T.solvedN}</small><b>${j.solved}</b></div><div><small>${T.myTotal}</small><b>${j.total}</b></div></div>
    ${(() => { const at = j.tierAt || [], lo = j.lv >= 1 ? at[j.lv - 1] : 0, hi = at[j.lv]; if (hi == null) return "";
      const f = Math.max(0, Math.min(1, (j.rating - lo) / (hi - lo)));
      return `<div class="arprog"><div class="arprogh">${arTier(j.lv)}<span>${lang === "en" ? `<b>${hi - j.rating}</b> to ${tierName(j.lv + 1)}` : `${tierName(j.lv + 1)}까지 <b>${hi - j.rating}</b>`}</span></div><div class="arbar"><i style="width:${(f * 100).toFixed(1)}%;background:${TIER_COL[tierKey(j.lv + 1)]}"></i></div></div>`; })()}
    ${(() => { let n = false; try { n = sessionStorage.getItem("hlArNew") === "1"; sessionStorage.removeItem("hlArNew"); } catch (e) {} return n ? `<div class="cmnote" style="margin-bottom:14px">${T.oauthNew}</div>` : ""; })()}
    <div class="arpanel armeset"><h3>${T.nickH}</h3><form id="arNick" class="arq"><input name="n" value="${esc(cm.me.nickname)}" maxlength="16"><button class="cmbtn sm pri">${T.change}</button><span class="arinfo"></span><span class="cmnick" style="flex-basis:100%"></span></form>
      <h3 style="margin-top:14px">${CMT[lang].avatarH}</h3><div id="arAv"><div class="arq"><label class="cmbtn sm">${CMT[lang].avatarPick}<input type="file" accept="image/jpeg,image/png,image/webp" hidden></label>
        <button class="cmbtn sm" type="button" data-del ${cm.me.avatar ? "" : "hidden"}>${CMT[lang].avatarDel}</button><span class="arinfo cmerr"></span></div></div>
      <h3 style="margin-top:14px">${T.linkH}</h3><div id="arIds" class="arids"></div></div>
    <div class="arpanel" id="arLabMe"></div>
    <div class="arpanel"><h3>${T.recent}</h3>${j.subs.length ? `<table class="cmtbl artbl"><tbody>${j.subs.map((s) => `<tr><td style="width:96px">${esc(arPeriodLabel(s))}</td>
      <td class="t"><a href="#/monthly/p/${s.problem_id}">${s.no}. ${esc(lang === "en" ? s.title_en : s.title_ko)}</a></td>
      <td style="width:110px"><b>${s.status === "graded" ? s.score + " / " + s.points : T[s.status] || s.status}</b></td><td style="width:130px">${cmShort(s.created_at)}</td></tr>`).join("")}</tbody></table>` : `<p class="arempty">${T.empty}</p>`}</div>`;
  cmAvatarForm(root.querySelector("#arAv"), () => { const h = root.querySelector(".cmtop h1"); if (h) h.innerHTML = `${cmAv(cm.me.nickname, "", cm.me.avatar)} ${esc(cm.me.nickname)} ${arTier(j.lv)}`; });
  const nf = root.querySelector("#arNick");
  const nickFree = cmNickCheck(nf.n, nf.querySelector(".cmnick"), cm.me.nickname);
  nf.onsubmit = async (e) => { e.preventDefault(); const info = nf.querySelector(".arinfo"); info.textContent = "";
    if (await nickFree() === false) { info.textContent = cmErr({code: "nickname_taken"}); return; }
    try { const r = await cmApi("PATCH", "/me", {nickname: nf.n.value.trim()}); cm.me.nickname = r.nickname; nf.n.value = r.nickname; info.textContent = T.done; arChip();
      const h = root.querySelector(".cmtop h1"); if (h) h.innerHTML = `${cmAv(cm.me.nickname, "", cm.me.avatar)} ${esc(cm.me.nickname)} ${arTier(j.lv)}`; } catch (er) { info.textContent = arErr(er); } };
  try {
    const idj = {identities:overview.identities||[],providers:overview.providers||ar.health?.oauth||[],has_pw:overview.has_password}, have = idj.identities.map((x) => x.provider), box = root.querySelector("#arIds");
    box.innerHTML = `<div class="oauth">${[...new Set(arProvs().concat(have))].map((p) => have.includes(p) ? `<span class="${p}">${OAUTH_ICON[p]}${(T.oauthWith[p] || p).replace(/로 계속하기|Continue with /g, "")} · ${T.connected}</span>`
      : idj.providers.includes(p) && arProvs().includes(p) ? `<a href="#" data-p="${p}" class="${p}">${OAUTH_ICON[p]}${(T.oauthWith[p] || p).replace(/로 계속하기|Continue with /g, "")} · ${T.link}</a>` : "").join("")}</div>
      ${idj.has_pw ? "" : `<form id="arPw" class="arq"><span>${T.pwSet}</span><input type="password" name="pw" placeholder="${T.pwNew}" minlength="8"><button class="cmbtn sm">${T.save}</button><span class="arinfo"></span></form>`}`;
    for (const a of box.querySelectorAll("a[data-p]")) a.onclick = async (e) => { e.preventDefault(); try { const t = await cmApi("POST", "/oauth/ticket"); sessionStorage.setItem("hlCmBack", "#/me"); arOauthStart(a.dataset.p, t.ticket); } catch (er) { cmToast(arErr(er)); } };
    const pf = box.querySelector("#arPw"); if (pf) pf.onsubmit = async (e) => { e.preventDefault(); try { await cmApi("POST", "/me/password", {password: pf.pw.value}); pf.querySelector(".arinfo").textContent = T.done; } catch (er) { pf.querySelector(".arinfo").textContent = arErr(er); } };
  } catch (e) {}
  if ((ar.health || {}).lab) {const x=overview; const el = root.querySelector("#arLabMe"); if (!el) return; const L = LBT[lang === "en" ? "en" : "ko"];
    el.innerHTML = `<h3>⏱ ${L.h}</h3><p style="margin:0 0 8px">${L.tokens(x.tokens)}${x.active ? ` · <b>${L.st[x.active.status]}</b>: ${esc(x.active.comp.toUpperCase())} ${x.active.year}` : ""}</p><a class="cmbtn sm" href="#/lab">${L.all}</a>`; }
  else { const el = root.querySelector("#arLabMe"); if (el) el.remove(); }
  root.querySelector("#arLogout").onclick = async () => { try { await cmApi("POST", "/logout"); } catch (e) {} cmTok(null); cm.me = null; location.hash = "#/monthly"; arChip(); };
}

/* ── exam mode: tokens, exams, marks ── */
const LBT = {
  ko: {h: "응시·채점 기록", sub: "실전 응시는 회차별 제한 시간에 맞춰 진행합니다. 이미 푼 답안은 시간 제한 없이 채점·첨삭만 받을 수 있습니다. 채점·첨삭은 한 시험 0.3토큰, 이론·실험 세트 합계 0.5토큰입니다.",
       tokens: (n) => `남은 실전 토큰 <b>${n}</b>개`, ledger: "토큰 기록", all: "응시·채점 기록", mine: "내 기록", none: "아직 응시·채점 기록이 없습니다.",
       start: "시작", grade: "채점 · 첨삭", half: "이전 채점 비용 (0.5)", grant: "받음", revoke: "회수", refund: "돌려받음", purchase: "구매", ad: "광고 시청 3회", cancel: "구매 환불",
       shopH: "토큰 충전", consent: "구매 안내를 읽었고, 만 19세 미만이면 보호자의 동의를 받았습니다.",
       buyNote: "카드 · 간편결제(토스페이먼츠). 쓰지 않은 토큰은 구매 후 7일 안에 환불을 요청할 수 있습니다(커뮤니티 문의). 토큰은 실전 답안과 별도 제출 답안의 채점·첨삭에 사용합니다.",
       payOff: "결제는 준비 중입니다.", tabP: "해외 카드 · USD", tabT: "국내 결제 · 원", tokU: () => "토큰", per: (x) => `개당 ${x}`, save: (p) => `${p}% 절약`,
       payTotal: "결제 금액", payNow: (x) => `${x} 결제하기`, methodsP: "Visa · Mastercard · AMEX · PayPal · Apple Pay · Google Pay", methodsT: "신용 · 체크카드 · 토스페이 · 카카오페이 · 네이버페이",
       morP: "결제는 Paddle.com이 판매자(Merchant of Record)로 처리하며, 현지 통화와 세금은 결제창에 표시됩니다. 쓰지 않은 토큰은 구매 후 14일 안에 환불을 요청할 수 있습니다.",
       payErr: "결제창을 열지 못했습니다. 잠시 뒤 다시 시도해 주세요.", payCfg: "결제 설정이 아직 끝나지 않아 결제창을 열 수 없습니다. 잠시 뒤 다시 시도해 주세요.", consentNeed: "구매 안내에 동의해 주세요.", adH: "광고 보고 충전", adWatch: "광고 보기", adParts: (k) => `광고 1편 = 토큰 1/3 · 지금 ${k}/3`,
       adNote: (d) => `휴대폰에서만 볼 수 있습니다. 하루 ${d}편까지(토큰 ${Math.floor(d / 3) || "1/3"}개분).`, adLoading: "광고를 불러오는 중…", adNone: "지금은 보여 줄 광고가 없습니다. 잠시 뒤 다시 시도해 주세요.",
       adMobile: "보상형 광고는 휴대폰 화면에서만 지원됩니다. 휴대폰으로 이 페이지를 열어 주세요.", adGot: (k, n) => `토큰 1/3을 받았습니다 (${k}/3)${n ? ` · 토큰 ${n}개` : ""}`, adToken: "광고 3편을 다 봐서 토큰 1개를 받았습니다!",
       adClosed: "광고를 끝까지 보지 않아 보상이 없습니다.", adDaily: (d) => `오늘은 광고를 ${d}편 다 보셨습니다. 내일 다시 오세요.`, adOff: "광고 충전은 준비 중입니다.", resume: "이어하기", active: "진행 중인 시험", total: "총점", pages: "보낸 쪽",
       st: {running: "실험 중", scanning: "스캔 중", grading: "채점 중", graded: "채점 완료", pending: "채점 대기", error: "채점 오류", empty: "제출 없음", ended: "채점 안 함"},
       payH: "채점 · 첨삭 받기", payNote: "채점하지 않고 끝낸 시험입니다. 보낸 답안은 7일 동안 보관되며, 그 안에 0.3토큰으로 채점과 첨삭(총평 · 고칠 습관 · 글씨)을 받을 수 있습니다.", payBtn: "0.3토큰으로 채점받기", payBusy: "채점하는 중… (1–2분)", payNo: "채점에 필요한 실전 토큰이 부족합니다. 위 «토큰 충전»에서 충전하세요.",
       why: {ocr_failed: "사진 원문을 읽지 못해 점수를 보류했습니다. 답안을 확인하고 재촬영 또는 검토가 필요합니다.", ocr_structure: "사진 원문은 보관했지만 풀이 구조를 확인하지 못해 점수를 보류했습니다. 관리자 검토가 필요합니다.", no_scheme: "이 실험의 채점 기준이 아직 등록되지 않아 관리자가 채점합니다.", no_grader: "AI 채점기가 연결되지 않아 관리자가 채점합니다.", no_solution: "이 실험은 공식 솔루션 파일이 없어 채점 기준표를 만들 수 없습니다.", no_official_points: "공식 해설에 배점이 없어 수치 점수를 확정하지 않았습니다."},
       err: "채점 서버가 응답하지 않았습니다. 관리자가 다시 채점합니다.", empty: "이 실험에서 보낸 쪽이 없습니다.", sol: "풀이 · 채점 기준", answer: "답안지", working: "Working sheet",
       del: "이 기록 지우기", delQ: "이 시험 기록과 사진을 지울까요? 토큰은 돌아오지 않습니다.", howGet: "응시는 무료이고, 실전 답안이나 이미 푼 답안의 채점·첨삭을 요청할 때 토큰을 씁니다. 토큰은 위 «토큰 충전»에서 사거나 광고로 모을 수 있습니다.",
       admin: "실전 모드 관리", grantH: "토큰 주기 / 회수", user: "아이디 또는 닉네임", delta: "개수 (+2, -1)", look: "조회", rubH: "채점 기준 (실험별)", load: "불러오기",
       queue: "채점 대기 시험", give: "점수 주기", regrade: "AI로 다시 채점", points: "만점",
       reportH: "성적표", examNo: "수험번호", cand: "응시자", exam: "시험", date: "응시일", pct: "백분율", rank: "순위", rankV: (k, n) => `${n}명 중 ${k}위`, top: "상위", avg: "응시자 평균", max: "최고",
       retryNote: "다시 응시한 시험입니다. 순위는 다른 응시자들의 첫 응시와 비교한 것입니다.", examList: "시험 목록",
       item: "채점 항목", evid: "근거", rulesH: "적용 규정", by: {code: "범위·검증", model: "AI 판단"}, sheetA: "답안지", sheetW: "연습지", page: "쪽",
       regH: "채점 규정", regNote: "엄격 채점: 읽을 수 없는 것은 응시자 책임이며 다시 읽어 주지 않습니다.", noSol: "이 실험은 공식 솔루션 파일이 없어 채점 기준표를 만들 수 없습니다.",
       rvH: "총평", rvGood: "잘한 점", rvHabits: "고쳐야 할 습관", rvHand: "글씨", rvPres: "답안 구성", rvRate: {clear: "또렷함", readable: "읽을 만함", hard: "알아보기 어려움"}, rvPages: "쪽",
       ref: "기준", refSave: "기준 점수 저장", refNote: "관리자만 보입니다: 사람이 매긴 기준 점수 — AI 채점 정확도 측정에 씁니다.", purged: "보관 기간이 지나 사진을 지웠습니다.",
       mH: "채점 비용 · 시간 · 정확도", mDays: "최근 30일", mExam: "시험 1회당", mUsd: "비용", mTok: "토큰 (입력 / 출력)", mCalls: "AI 호출", mTime: "채점 시간", mWait: "제출→채점 완료",
       mStep: "단계별", mAcc: "정확도 (관리자 기준 점수와 비교)", mMae: "문항당 평균 차이", mExact: "일치한 문항", mTaskDiff: "실험 총점 차이 (만점 대비)", mItems: "비교한 문항",
       mStore: "답안 사진", mKeep: (h) => h == null ? "보관 중 (파기 꺼짐)" : `채점 ${h}시간 뒤 파기`, mNone: "아직 기록이 없습니다.", mRecent: "최근 채점"},
  en: {h: "Attempts & grading history", sub: "Timed attempts follow each session's time limit. Submit work already solved for grading and feedback without a timer. Grading costs 0.3 token per exam, or 0.5 token total for a theory + experiment set.",
       tokens: (n) => `Exam tokens left: <b>${n}</b>`, ledger: "Token history", all: "Attempts & grading history", mine: "My records", none: "No attempts or grading submissions yet.",
       start: "start", grade: "grading and review", half: "Previous grading fee (0.5)", grant: "received", revoke: "taken back", refund: "refunded", purchase: "bought", ad: "3 ads watched", cancel: "purchase refunded",
       shopH: "Get tokens", consent: "I have read the purchase terms; if I am under 19, a parent or guardian agreed.",
       buyNote: "Card or easy pay (Toss Payments). Unused tokens can be refunded within 7 days of purchase (ask in the community). Tokens pay for grading timed attempts or work submitted separately.",
       payOff: "Payments are not open yet.", tabP: "International · USD", tabT: "Korea · KRW", tokU: (n) => n > 1 ? "tokens" : "token", per: (x) => `${x} each`, save: (p) => `save ${p}%`,
       payTotal: "Total", payNow: (x) => `Pay ${x}`, methodsP: "Visa · Mastercard · AMEX · PayPal · Apple Pay · Google Pay", methodsT: "Cards · Toss Pay · Kakao Pay · Naver Pay",
       morP: "Payments are processed by Paddle.com, our Merchant of Record; your local currency and tax are shown at checkout. Unused tokens can be refunded within 14 days of purchase.",
       payErr: "The checkout could not open. Please try again in a moment.", payCfg: "Checkout is not set up yet, so it cannot open. Please try again later.", consentNeed: "Please agree to the purchase terms.", adH: "Watch ads", adWatch: "Watch an ad", adParts: (k) => `1 ad = 1/3 token · now ${k}/3`,
       adNote: (d) => `Phones only. Up to ${d} ads a day.`, adLoading: "Loading the ad…", adNone: "No ad is available right now. Please try again later.",
       adMobile: "Rewarded ads only run on a phone screen. Open this page on your phone.", adGot: (k, n) => `You got 1/3 of a token (${k}/3)${n ? ` · ${n} tokens` : ""}`, adToken: "Three ads watched: you got a token!",
       adClosed: "The ad was closed before the end, so there is no reward.", adDaily: (d) => `You have watched today's ${d} ads. Come back tomorrow.`, adOff: "Ads are not open yet.", resume: "Resume", active: "In progress", total: "Total", pages: "Pages sent",
       st: {running: "experiments running", scanning: "scanning", grading: "grading", graded: "graded", pending: "waiting for a grader", error: "grading error", empty: "nothing sent", ended: "not graded"},
       payH: "Get it graded and reviewed", payNote: "This sitting ended ungraded. Its pages are kept for 7 days; within that time 0.3 token gets them graded and reviewed (summary, habits to fix, handwriting).", payBtn: "Grade it for 0.3 token", payBusy: "Grading… (1–2 minutes)", payNo: "You do not have enough exam tokens for grading. Get some under «Get tokens» on the exam mode page.",
       why: {ocr_failed: "The original photo could not be read. The score is held for a retake or review.", ocr_structure: "The original text is saved, but the solution structure could not be verified. The score is held for manual review.", no_scheme: "This experiment's marking scheme is not entered yet, so an admin will grade it.", no_grader: "No AI grader is connected, so an admin will grade it.", no_solution: "This experiment has no official solution file, so no marking scheme could be drawn.", no_official_points: "The published solution has no point values, so no numerical score has been assigned."},
       err: "The grading server did not answer. An admin will grade it again.", empty: "No pages were sent for this experiment.", sol: "Solution & marking scheme", answer: "Answer sheet", working: "Working sheet",
       del: "Delete this record", delQ: "Delete this exam and its photos? The token is not given back.", howGet: "Sitting is free; tokens pay for grading and feedback on timed attempts or work already solved. Get tokens under «Get tokens» above, by buying them or watching ads.",
       admin: "Exam mode admin", grantH: "Give / take tokens", user: "username or nickname", delta: "how many (+2, -1)", look: "Look up", rubH: "Marking schemes (per experiment)", load: "Load",
       queue: "Exams waiting for a grader", give: "Give score", regrade: "Regrade with AI", points: "full marks",
       reportH: "Score report", examNo: "Candidate no.", cand: "Candidate", exam: "Exam", date: "Date", pct: "Percentage", rank: "Rank", rankV: (k, n) => `${k} of ${n}`, top: "top", avg: "Average", max: "Best",
       retryNote: "This was a second sitting; the rank compares it with the other candidates' first sittings.", examList: "Exam list",
       item: "Item", evid: "Evidence", rulesH: "Rules", by: {code: "interval / check", model: "AI judgement"}, sheetA: "answer sheet", sheetW: "working sheet", page: "p.",
       regH: "Grading regulation", regNote: "Strict marking: whatever cannot be read is the candidate's responsibility and is not re-read.", noSol: "This experiment has no official solution file, so no marking scheme could be drawn.",
       rvH: "Review", rvGood: "Done well", rvHabits: "Habits to fix", rvHand: "Handwriting", rvPres: "Presentation", rvRate: {clear: "clear", readable: "readable", hard: "hard to read"}, rvPages: "p.",
       ref: "Ref.", refSave: "Save reference marks", refNote: "Admins only: marks given by a person — used to measure how accurate the AI grading is.", purged: "The photo was removed after its keeping time.",
       mH: "Grading cost · time · accuracy", mDays: "last 30 days", mExam: "Per exam", mUsd: "Cost", mTok: "Tokens (in / out)", mCalls: "AI calls", mTime: "Grading time", mWait: "Submitted → graded",
       mStep: "By step", mAcc: "Accuracy (against the admins' reference marks)", mMae: "Mean difference per item", mExact: "Items that agree", mTaskDiff: "Experiment total difference (of full marks)", mItems: "Items compared",
       mStore: "Answer photos", mKeep: (h) => h == null ? "kept (removal off)" : `removed ${h} h after grading`, mNone: "Nothing recorded yet.", mRecent: "Recent gradings"}};
const lbt = () => LBT[lang === "en" ? "en" : "ko"];
const arIsContest = s => s && s.comp === "kmo" && s.purpose === "review" && typeof s.examId === "string";
const arReviewOnly = s => !!(s && (s.review_only || arIsContest(s)));
const arQualitative = x => !!(x && (x.grading_mode === "qualitative_review" || x.reference === "published_problem_only"));
const arLabHasScore = x => !!(x && Number.isFinite(x.score) && Number.isFinite(x.points) && x.points > 0);
const arLabModeLabel = s => arReviewOnly(s) ? (lang === "en" ? "Grading & feedback" : "채점·첨삭") : (lang === "en" ? "Timed attempt" : "실전 응시");
const arLabScoreLabel = x => arLabHasScore(x) ? `${x.score} / ${x.points}` : x.status === "graded" ? (lang === "en" ? "Feedback complete · no score" : "첨삭 완료 · 점수 없음") : "–";
const arLabCost = s => Number.isFinite(s?.cost) && s.cost >= 0 ? s.cost : s?.kind === "mixed" ? 0.5 : 0.3;
function arLabLabels(s) {
  const english = lang === "en", cost = arLabCost(s), L = {...lbt(),
    payNote: english ? `This work has not been graded. Its pages are kept for seven days; grading and feedback cost ${cost} token.` : `아직 채점하지 않은 답안입니다. 제출한 쪽은 7일 동안 보관되며, 채점·첨삭 비용은 ${cost}토큰입니다.`,
    payBtn: english ? `Grade it for ${cost} token` : `${cost}토큰으로 채점받기`};
  return arReviewOnly(s) ? {...L,
    reportH: english ? "Grading & feedback report" : "채점·첨삭 결과",
    examNo: english ? "Submission no." : "접수번호", cand: english ? "Submitted by" : "제출자",
    exam: english ? "Competition / paper" : "대회·문제", date: english ? "Received" : "접수일",
    examList: english ? "Papers for grading" : "채점할 문제 목록", active: english ? "Submission in progress" : "답안 제출 중",
    empty: english ? "No answer pages were submitted for this task." : "이 문항에 제출한 답안이 없습니다.",
    regH: english ? "Learning-review rules" : "학습용 검토 규정",
    regNote: english ? "This is a learning review. If no official solution or marking scheme is available, the work and its evidence are reviewed without a numerical score." : "학습용 채점·첨삭입니다. 공식 해설·채점 기준이 없으면 점수 없이 풀이와 근거를 검토합니다.",
    delQ: english ? "Delete this submission record and its photos? The token is not given back." : "이 제출 기록과 사진을 지울까요? 토큰은 돌아오지 않습니다.",
    st: {...L.st,running:english?"preparing answers":"답안 준비 중",scanning:english?"submitting answers":"답안 제출 중",graded:english?"review complete":"채점·첨삭 완료"}
  } : L;
}
function arLabHref(s) {
  if (arIsContest(s)) return `sim/contest-exam.html?id=${encodeURIComponent(s.examId)}&review=${encodeURIComponent(s.id)}&lang=${lang === "en" ? "en" : "ko"}`;
  return s && s.entry ? `sim/exam.html${s.entry}&lang=${lang}` : "";
}
/* the catalogue's solution sheet for an exam's experiment, when the site has one */
function arLabSol(s, task) {
  if (arIsContest(s)) return "";
  const c = DATA[s.comp], y = c && c.years.find((x) => x.y === s.year), p = y && y.problems.find((x) => x.id === task || (typeof examTask === "function" && examTask(x) === task)), v = p && p.files && p.files.sol;
  return typeof v === "string" ? v : v ? (v[lang] || v.ko || v.en) : "";
}
function arLedgerHtml(rows){
  const L=lbt(),english=lang==='en';
  return rows.length?`<table class="cmtbl artbl"><tbody>${rows.map(x=>{
    let pricing=null;try{const v=JSON.parse(x.note);if(v?.pricing_version===2&&Number.isFinite(v.cost))pricing=v;}catch(e){}
    const delta=x.note==='half'?-0.5:Number(x.delta),amount=Number.isFinite(delta)?Math.round(delta*10)/10:0;
    const pair=pricing&&Number.isSafeInteger(pricing.paired_with)&&pricing.paired_with>0?pricing.paired_with:null;
    const extra=pricing?(pair?` · ${english?'Set discount':'세트 할인'} ${Number(pricing.discount)||0.1}${english?' token':'토큰'} · <a href="#/lab/${pair}">#${pair}</a>`:'')
      :x.note==='half'?' · '+L.half:x.note?' · '+esc(x.note):'';
    return `<tr><td style="width:80px"><b style="color:${amount<0?'#c0392b':'#1e8449'}">${amount>0?'+':amount<0?'−':''}${Math.abs(amount)}</b></td><td class="t">${L[x.reason]||esc(x.reason)}${x.exam_key?' · '+esc(x.exam_key.toUpperCase()):''}${extra}</td><td style="width:130px">${cmShort(x.created_at)}</td></tr>`;
  }).join('')}</tbody></table>`:'';
}
async function arLabList(root, alive,bootstrap) {
  const L = lbt();
  const [boot,shop]=await Promise.all([bootstrap||(typeof cmLabBootstrap==='function'?cmLabBootstrap():cmApi('GET','/lab/bootstrap?include=sessions,health')),bootstrap?.shop||cmApi('GET','/pay/config').catch(()=>({}))]);if(!alive())return;
  if(!boot.user){try{sessionStorage.setItem('hlCmBack','#/lab');}catch(e){}location.hash='#/login';return;}
  cm.me=boot.user;const act=boot.active,tk=boot,ls={sessions:boot.sessions||[]};
  root.innerHTML = `
    <div class="cmtop"><div><h1>📄 ${L.h}</h1><p>${L.sub}</p></div>${arModelTestLink()}</div>
    <div class="arstats"><div><small>${lang === "en" ? "Tokens" : "실전 토큰"}</small><b id="lbTokN">${tk.tokens}</b></div><div><small>${L.mine}</small><b>${ls.sessions.length}</b></div></div>
    ${arShopHtml(shop, tk.parts || 0)}
    ${act ? `<div class="arpanel"><h3>${arLabLabels(act).active}</h3><p style="margin:0 0 8px"><b>${esc(act.comp.toUpperCase())} ${act.year}</b> · ${arLabModeLabel(act)} · ${arLabLabels(act).st[act.status]}</p>
      ${arLabHref(act) ? `<a class="cmbtn pri" href="${esc(arLabHref(act))}">${L.resume}</a>` : ""}</div>` : ""}
    <div class="arpanel"><h3>${L.mine}</h3>${ls.sessions.length ? `<table class="cmtbl artbl"><tbody>${ls.sessions.map((x) => `<tr>
      <td class="t"><a href="#/lab/${x.id}"><b>${esc(x.comp.toUpperCase())} ${x.year}</b> ${esc(x.tasks.join(" + "))}</a><small class="arnote">${arLabModeLabel(x)}</small></td>
      <td style="width:150px">${arLabLabels(x).st[x.status] || esc(x.status)}</td><td style="width:110px"><b>${arLabScoreLabel(x)}</b></td>
      <td style="width:130px">${cmShort(x.created_at)}</td></tr>`).join("")}</tbody></table>` : `<p class="arempty">${L.none}</p>`}</div>
    <div class="arpanel"><details id="lbLedger"><summary style="cursor:pointer;font-weight:700">${L.ledger}</summary><p class="arempty">${L.howGet}</p><div id="lbLedgerBody"></div></details></div>`;
  arShopWire(root,shop);
  const ledger=root.querySelector('#lbLedger');let loading=false,loaded=false;
  if(ledger)ledger.addEventListener('toggle',async()=>{if(!ledger.open||loaded||loading)return;loading=true;const owner=cmTok();try{const r=await cmApi('GET','/lab/tokens');if(!alive()||owner!==cmTok())return;root.querySelector('#lbLedgerBody').innerHTML=arLedgerHtml(r.ledger||[]);loaded=true;}catch(e){if(alive())root.querySelector('#lbLedgerBody').textContent=arErr(e);}finally{loading=false;}});
}

/* ── getting tokens: buying (Paddle in USD, Toss Payments in KRW) and rewarded video ads (a third each) ──
   laid out like a top-up page: pick a pack, one total, one pay button */
function arShopLists(c) {
  const L = lbt(), out = [];
  const usd = (v) => v == null ? "" : "$" + (+v).toFixed(2), krw = (v) => lang === "en" ? "₩" + Math.round(v).toLocaleString() : Math.round(v).toLocaleString() + "원";
  if (c.paddle) out.push({k: "p", tab: L.tabP, attr: "data-ppack", fmt: usd, methods: L.methodsP, note: L.morP, packs: c.paddle.packs.map((p) => ({id: p.id, n: p.tokens, v: p.usd}))});
  if (c.pay) out.push({k: "t", tab: L.tabT, attr: "data-pack", fmt: krw, methods: L.methodsT, note: L.buyNote, packs: c.pay.packs.map((p) => ({id: p.id, n: p.tokens, v: p.krw}))});
  for (const x of out) {
    const base = x.packs.reduce((m, p) => p.v != null && (!m || p.n < m.n) ? p : m, null);
    x.packs.forEach((p) => { p.save = base && p.v != null ? Math.round((1 - p.v / p.n / (base.v / base.n)) * 100) : 0; });
    x.sel = x.packs[Math.min(1, x.packs.length - 1)].id;                       // the middle pack, as most top-up pages do
  }
  return out;
}
function arShopHtml(c, parts) {
  const L = lbt();
  if (!c || (!c.pay && !c.paddle && !c.ads)) return "";
  const lists = arShopLists(c), cur = lists[0];
  const row = (x, p) => `<button type="button" class="arpk" ${x.attr}="${esc(p.id)}" aria-pressed="${p.id === x.sel}">
      <span class="arpk-n"><b>${p.n}</b>${L.tokU(p.n)}</span>
      <span class="arpk-u">${p.v != null ? L.per(x.fmt(p.v / p.n)) : ""}${p.save >= 5 ? `<em>${L.save(p.save)}</em>` : ""}</span>
      <span class="arpk-v">${x.fmt(p.v)}</span></button>`;
  const selV = cur ? cur.packs.find((p) => p.id === cur.sel).v : null;
  return `<div class="arpanel arshop" id="lbShop"><h3>${L.shopH}</h3>
    ${lists.length > 1 ? `<div class="arseg" role="tablist">${lists.map((x, i) => `<button type="button" role="tab" data-tab="${x.k}" aria-selected="${i === 0}">${x.tab}</button>`).join("")}</div>` : ""}
    ${lists.map((x, i) => `<div class="arpks" data-list="${x.k}"${i ? " hidden" : ""}>${x.packs.map((p) => row(x, p)).join("")}</div>`).join("")}
    ${cur ? `<div class="arpay">
      <div class="arpay-sum"><span>${L.payTotal}</span><b id="lbTotal">${cur.fmt(selV)}</b></div>
      <label class="arpay-ok"><input type="checkbox" id="lbConsent"> <span>${L.consent}</span></label>
      <button type="button" class="cmbtn pri arpay-go" id="lbPay">${L.payNow(cur.fmt(selV))}</button>
      <p class="arpay-fine" id="lbFine">${cur.methods}<br>${cur.note}</p></div>` : `<p class="arempty">${L.payOff}</p>`}
    ${c.ads ? `<div class="arad"><div><b>${L.adH}</b>
      <div class="arad-row"><span class="arad-bar" id="lbBar">${[0, 1, 2].map((i) => `<i${i < parts ? ' class="on"' : ""}></i>`).join("")}</span><small id="lbParts">${L.adParts(parts)}</small></div></div><button type="button" class="cmbtn" id="lbAd">${L.adWatch}</button></div>
      <p class="arpay-fine">${L.adNote(c.ads.daily)}</p>` : ""}
    <p id="lbShopMsg" class="arinfo" style="margin:8px 0 0"></p></div>`;
}
function arLoad(src, test) {
  return new Promise((ok, no) => { if (test()) return ok(); const sc = document.createElement("script"); sc.src = src; sc.async = true; sc.onload = () => ok(); sc.onerror = () => no(new Error("load")); document.head.append(sc); });
}
let arAd = null, arPaddle = {ready: false, order: null, loaded: false, done: null};                                                                  // the rewarded ad being shown: {slot, nonce, granted}
function arShopWire(root, c) {
  const L = lbt(), msg = (t) => { const m = document.querySelector("#lbShopMsg"); if (m) m.textContent = t; };
  const lists = arShopLists(c || {}), pay = root.querySelector("#lbPay");
  let cur = lists[0];
  const show = () => {
    const p = cur.packs.find((x) => x.id === cur.sel);
    root.querySelector("#lbTotal").textContent = cur.fmt(p.v);
    pay.textContent = L.payNow(cur.fmt(p.v));
    root.querySelector("#lbFine").innerHTML = `${cur.methods}<br>${cur.note}`;
  };
  root.querySelectorAll("#lbShop [data-tab]").forEach((t) => t.onclick = () => {
    cur = lists.find((x) => x.k === t.dataset.tab);
    root.querySelectorAll("#lbShop [data-tab]").forEach((x) => x.setAttribute("aria-selected", x === t));
    root.querySelectorAll("#lbShop [data-list]").forEach((x) => x.hidden = x.dataset.list !== cur.k);
    show();
  });
  for (const x of lists) root.querySelectorAll(`#lbShop [${x.attr}]`).forEach((b) => b.onclick = () => {
    x.sel = b.getAttribute(x.attr);
    root.querySelectorAll(`#lbShop [${x.attr}]`).forEach((y) => y.setAttribute("aria-pressed", y === b));
    if (x === cur) show();
  });
  if (pay) pay.onclick = async () => {
    if (!root.querySelector("#lbConsent").checked) { msg(L.consentNeed); return; }
    pay.disabled = true; msg("");
    try { await (cur.k === "p" ? arPaddleOpen(cur.sel) : arTossOpen(cur.sel)); }
    catch (e) { msg(e && e.code ? arErr(e) : (e && e.message) || "error"); pay.disabled = false; }
  };
  const back = location.origin + location.pathname.replace(/[^/]*$/, "") + "pay.html";
  async function arTossOpen(pack) {
    const o = await cmApi("POST", "/pay/order", {pack});
    await arLoad("https://js.tosspayments.com/v2/standard", () => !!window.TossPayments);
    const payment = window.TossPayments(c.pay.client_key).payment({customerKey: window.TossPayments.ANONYMOUS});
    await payment.requestPayment({method: "CARD", amount: {currency: "KRW", value: o.amount}, orderId: o.order_id, orderName: o.order_name, successUrl: back, failUrl: back});
  }
  /* Paddle: Paddle.js once per page, the overlay checkout with the pack's price and our order id; after payment
     pay.html is told the transaction, and the server checks it with Paddle (the signed webhook adds the tokens too).
     A checkout that fails before it has loaded (e.g. the account's default payment link not set) is closed and
     explained here instead of Paddle's bare «Something went wrong». */
  async function arPaddleOpen(pack) {
    const o = await cmApi("POST", "/pay/order", {pack, provider: "paddle"});
    await arLoad("https://cdn.paddle.com/paddle/v2/paddle.js", () => !!window.Paddle);
    arPaddle.order = o.order_id; arPaddle.loaded = false;
    arPaddle.done = (text) => { const b = document.querySelector("#lbPay"); if (b) b.disabled = false; if (text) { const m = document.querySelector("#lbShopMsg"); if (m) m.textContent = text; } };
    if (!arPaddle.ready) {
      if (c.paddle.env === "sandbox") window.Paddle.Environment.set("sandbox");
      window.Paddle.Initialize({token: c.paddle.token, eventCallback: (ev) => {
        const n = ev && ev.name;
        if (n === "checkout.loaded") arPaddle.loaded = true;
        if (n === "checkout.completed" && arPaddle.order) location.href = `${back}?paddle=1&order=${encodeURIComponent(arPaddle.order)}&txn=${encodeURIComponent((ev.data && ev.data.transaction_id) || "")}`;
        if (n === "checkout.closed") arPaddle.done();
        if (n === "checkout.error" && !arPaddle.loaded) {
          console.warn("Paddle checkout", ev.detail || ev.code);
          try { window.Paddle.Checkout.close(); } catch (e) {}
          arPaddle.done(/default_checkout_url|domain|not_approved|forbidden/.test(ev.detail || "") ? lbt().payCfg : lbt().payErr);
        }
      }});
      arPaddle.ready = true;
    }
    window.Paddle.Checkout.open({items: [{priceId: o.price_id, quantity: 1}], customData: {order_id: o.order_id},
      settings: {displayMode: "overlay", locale: lang === "en" ? "en" : "ko", successUrl: `${back}?paddle=1&order=${encodeURIComponent(o.order_id)}`}});
  }
  const ad = root.querySelector("#lbAd");
  if (ad) ad.onclick = async () => {
    ad.disabled = true; msg(L.adLoading);
    let st;
    try { st = await cmApi("POST", "/ads/start"); }
    catch (e) { msg(e.code === "ads_daily" ? L.adDaily(c.ads.daily) : e.code === "ads_off" ? L.adOff : arErr(e)); ad.disabled = false; return; }
    try { await arLoad("https://securepubads.g.doubleclick.net/tag/js/gpt.js", () => !!(window.googletag && window.googletag.apiReady)); } catch (e) { msg(L.adNone); ad.disabled = false; return; }
    const gt = window.googletag;
    gt.cmd.push(() => {
      const slot = gt.defineOutOfPageSlot(c.ads.unit, gt.enums.OutOfPageFormat.REWARDED);
      if (!slot) { msg(L.adMobile); ad.disabled = false; return; }                 // not a phone screen
      arAd = {slot, nonce: st.nonce, granted: false, end: arAdEnd, claim: arAdClaim};     // the listeners below call this page's own handlers
      slot.addService(gt.pubads());
      if (!arShopWire.hooked) {
        arShopWire.hooked = true;
        gt.pubads().addEventListener("rewardedSlotReady", (e) => { if (arAd && e.slot === arAd.slot) e.makeRewardedVisible(); });
        gt.pubads().addEventListener("slotRenderEnded", (e) => { if (arAd && e.slot === arAd.slot && e.isEmpty) arAd.end(lbt().adNone); });
        gt.pubads().addEventListener("rewardedSlotGranted", (e) => { if (arAd && e.slot === arAd.slot) { arAd.granted = true; arAd.claim(arAd.nonce); } });
        gt.pubads().addEventListener("rewardedSlotClosed", (e) => { if (arAd && e.slot === arAd.slot) arAd.end(arAd.granted ? null : lbt().adClosed); });
      }
      gt.enableServices(); gt.display(slot);
    });
  };
  function arAdEnd(text) { if (arAd) { try { window.googletag.destroySlots([arAd.slot]); } catch (e) {} } arAd = null; if (text) msg(text); if (ad) ad.disabled = false; }
  async function arAdClaim(nonce, again) {
    try {
      const r = await cmApi("POST", "/ads/claim", {nonce});
      const n = root.querySelector("#lbTokN"), pp = root.querySelector("#lbParts"); if (n) n.textContent = r.tokens; if (pp) pp.textContent = L.adParts(r.parts); root.querySelectorAll("#lbBar i").forEach((x, i) => x.classList.toggle("on", i < r.parts));
      msg(r.parts === 0 ? L.adToken : L.adGot(r.parts, 0));
    } catch (e) {
      if (e.code === "too_soon" && !again) { setTimeout(() => arAdClaim(nonce, true), 6000); return; }
      msg(e.code === "ads_daily" ? L.adDaily(c.ads.daily) : arErr(e));
    }
  }
}
/* one experiment graded from the images: per item the mark, how it was decided, where its evidence is and the rules that cost marks */
function arLabItems(x, reg, rev) {
  if (arQualitative(x)) return arLabQualitative(x);
  const L = lbt(), T = arT(), ref = (id) => { const r = rev && rev.list.find((y) => y.task === rev.task && y.item_id === id); return r ? r.ref_points : ""; }, rule = (id) => { const r = reg && reg.rules.find((y) => y.id === id); return `<span class="arrule" title="${esc(r ? (lang === "en" ? r.en : r.ko) : id)}">${esc(id)}</span>`; };
  return `<div class="arres ${x.score >= x.points ? "ok" : ""}"><b>${T.score}</b><span>${x.score} / ${x.points}${T.pts}</span>${x.grader ? `<small>${T.grader}: ${esc(x.grader)}${x.regulation ? " · " + esc(x.regulation) : ""}</small>` : ""}</div>
    <table class="cmtbl artbl"><thead><tr><th style="width:40%">${L.item}</th><th style="width:96px">${T.score}</th><th>${L.evid}</th><th style="width:90px">${L.rulesH}</th>${rev ? `<th style="width:76px">${L.ref}</th>` : ""}</tr></thead><tbody>
    ${x.items.map((i) => `<tr><td class="t"><b>${esc(i.id)}</b> ${esc(i.what || "")}${i.note ? `<div class="arnote">${esc(i.note)}</div>` : ""}</td>
      <td><b>${i.got}</b>/${i.points}<div class="ardec ${i.decision}">${T[i.decision] || ""}</div><div class="arby">${L.by[i.by] || ""}</div></td>
      <td class="t">${i.page ? `${L.page === "p." ? "p." + i.page : i.page + L.page} · ${i.sheet === "answer" ? L.sheetA : L.sheetW}` : "—"}${i.value != null ? ` · <q>${esc(i.value)}</q>` : ""}</td>
      <td>${(i.rules || []).map(rule).join(" ")}</td>${rev ? `<td><input data-ref="${esc(i.id)}" type="number" step="0.1" min="0" max="${i.points}" value="${ref(i.id)}" style="width:64px"></td>` : ""}</tr>`).join("")}</tbody></table>
    ${rev ? `<p class="arempty" style="margin:6px 0">${L.refNote} <button class="cmbtn sm" data-rev="${esc(rev.task)}">${L.refSave}</button></p>` : ""}
    ${(x.feedback || []).length ? `<h4 class="arh4">${T.feedback}</h4><ul class="arfb">${x.feedback.map((f) => `<li class="${f.kind}"><em>${f.kind === "good" ? T.good : T.fix}</em>${f.label ? `<q>${esc(f.label)}</q> ` : ""}${esc(f.note)}</li>`).join("")}</ul>` : ""}
    ${arLabReview(x.review)}`;
}
/* A problem-based learning review has evidence and feedback, without a fabricated mark. */
function arLabQualitative(x) {
  const english=lang==="en", L=lbt(), T=arT();
  return `<div class="cmnote">${english?"Learning feedback based on the published problem and your submitted work. No official solution or marking scheme is available, so no numerical score is assigned.":"공개 문제와 제출한 답안을 바탕으로 한 학습용 첨삭입니다. 공식 해설·채점 기준이 없어 수치 점수를 매기지 않습니다."}</div>
    ${Array.isArray(x.evidence)&&x.evidence.length?`<table class="cmtbl artbl"><thead><tr><th>${L.page}</th><th>${L.evid}</th><th>${T.feedback}</th></tr></thead><tbody>${x.evidence.map(e=>`<tr><td>${e.page?esc(e.page):"—"}</td><td class="t">${esc(e.quote||"")}</td><td class="t">${esc(e.note||"")}</td></tr>`).join("")}</tbody></table>`:""}
    ${(x.feedback||[]).length?`<h4 class="arh4">${T.feedback}</h4><ul class="arfb">${x.feedback.map(f=>`<li class="${f.kind==="good"?"good":"fix"}"><em>${f.kind==="good"?T.good:T.fix}</em>${f.label?`<q>${esc(f.label)}</q> `:""}${esc(f.note||"")}</li>`).join("")}</ul>`:""}
    ${arLabReview(x.review)}`;
}
/* the coach's review of one experiment: overall, what went well, habits to fix, handwriting, presentation */
function arLabReview(r) {
  if (!r || !r.summary) return "";
  const L = lbt();
  return `<div class="arpanel" data-review style="margin:12px 0 0;background:var(--paper,rgba(127,127,127,.05))"><h4 class="arh4" style="margin-top:0">📝 ${L.rvH}</h4><p style="margin:0 0 8px">${esc(r.summary)}</p>
    ${(r.strengths || []).length ? `<b>${L.rvGood}</b><ul class="arfb">${r.strengths.map((x) => `<li class="good">${esc(x)}</li>`).join("")}</ul>` : ""}
    ${(r.habits || []).length ? `<b>${L.rvHabits}</b><ul class="arfb">${r.habits.map((h) => `<li class="fix"><em>${esc(h.habit)}</em> → ${esc(h.fix)}${(h.pages || []).length ? ` <small>(${h.pages.map((n) => L.rvPages === "p." ? "p." + n : n + L.rvPages).join(", ")})</small>` : ""}</li>`).join("")}</ul>` : ""}
    ${r.handwriting ? `<p style="margin:6px 0 0"><b>${L.rvHand}</b> · ${L.rvRate[r.handwriting.rating] || ""} — ${esc(r.handwriting.notes)}</p>` : ""}
    ${r.presentation ? `<p style="margin:6px 0 0"><b>${L.rvPres}</b> — ${esc(r.presentation)}</p>` : ""}</div>`;
}
let arNetworkPromise=null;
async function arWatchLab(root,alive,id,session){
  if(typeof document!=='object')return;
  try{const network=window.HLExamNetwork||await(arNetworkPromise||(arNetworkPromise=import('./sim/exam-network.js').then(()=>window.HLExamNetwork).catch(e=>{arNetworkPromise=null;throw e;})));if(!alive())return;
    let signature=network.sessionSignature(session);
    ar.poller?.dispose();ar.poller=network.createPoll({active:()=>{if(!alive()){ar.poller?.dispose();return false;}return true;},task:async()=>{const r=await cmApi('GET','/lab/sessions/'+id);if(!alive())return false;const next=network.sessionSignature(r.session),changed=signature!==next;signature=next;if(changed)await arLabOne(root,alive,id,r.session);return changed;}});ar.poller.start();
  }catch(e){}
}
async function arLabOne(root, alive, id,preloaded) {
  ar.poller?.dispose();ar.poller=null;
  const T = arT();
  if (!cm.me) { try { sessionStorage.setItem("hlCmBack", "#/lab/" + id); } catch (e) {} location.hash = "#/login"; return; }
  const s = preloaded||(await cmApi("GET", `/lab/sessions/${id}`)).session; if (!alive()) return;
  const isContest = arIsContest(s), reviewOnly = arReviewOnly(s), english = lang === "en", L = isContest ? {...arLabLabels(s),
    resume: english ? "Open answer submission / review" : "답안 제출·검토 화면 열기",
    reportH: english ? "Written-proof learning review" : "서술형 학습용 검토 기록", total: english ? "Reference score" : "학습용 참고점수",
    date: english ? "Review received" : "채점 접수 시각", empty: english ? "No proof was submitted for this question." : "이 문항에 제출된 풀이가 없습니다.",
    regH: english ? "HaslaLab learning-review rules" : "HaslaLab 학습용 검토 규칙",
    regNote: english ? "AI reference scores are not official KMO marking. Uncertain scans or arguments await manual review; compare OCR with the original before submitting." : "AI 참고점수는 공식 KMO 채점이 아닙니다. 판독·논증이 불확실하면 관리자 검토를 기다리며, OCR은 원본과 대조해 제출합니다.",
    st: {...lbt().st, scanning: english ? "preparing answers" : "답안 제출 준비", grading: english ? "under review" : "검토 중", graded: english ? "review complete" : "검토 완료", pending: english ? "awaiting manual review" : "관리자 검토 대기", ended: english ? "review not requested" : "검토 미신청"},
    why: Object.fromEntries(["needs_confirmation", "no_grader", "problem_unavailable", "uncertain_proof", "review_disagreement", "grader_unavailable", "answer_too_long", "scan_unavailable", "scan_too_large"].map(key => [key, english ? "The proof or review evidence needs manual checking. No score is final yet." : "답안 또는 검토 근거를 확인할 필요가 있어 관리자 검토를 기다립니다. 아직 확정된 점수는 없습니다."]))
  } : arLabLabels(s);
  const per = (s.detail && s.detail.tasks) || {}, open = s.status === "running" || s.status === "scanning";
  const comparison = !isContest && window.labComparison?.hasScore?.(s) && typeof window.labComparison.mount === 'function';
  if (!alive()) return;
  root.innerHTML = `
    <div class="cmtop"><div><h1>${reviewOnly?"✎":"⏱"} ${esc(s.comp.toUpperCase())} ${s.year} · ${esc(s.tasks.join(" + "))}</h1><p>${arLabModeLabel(s)} · ${cmFull(s.started_at).slice(0, 16)} · ${L.st[s.status] || esc(s.status)}</p></div>
      <div style="display:flex;gap:6px"><a class="cmbtn sm" href="#/${esc(s.comp)}/${reviewOnly?"review":"exam"}">${L.examList}</a><a class="cmbtn sm" href="#/lab">${L.all}</a>${(open || isContest) && arLabHref(s) ? `<a class="cmbtn sm pri" href="${esc(arLabHref(s))}">${L.resume}</a>` : ""}</div></div>
    ${isContest ? `<div class="cmnote">${L.regNote}</div>` : ""}
    <div class="arpanel arrep"><h3>📄 ${L.reportH}</h3><table class="cmtbl artbl ar-score-meta"><tbody>
      <tr><th>${L.examNo}</th><td><b>HL-${esc((s.comp + s.year).toUpperCase())}-${String(s.id).padStart(6, "0")}</b></td><th>${L.cand}</th><td>${esc(s.nickname || cm.me.nickname)}</td></tr>
      <tr><th>${L.exam}</th><td>${esc(s.comp.toUpperCase())} ${s.year} · ${esc(s.tasks.join(" + "))}</td><th>${L.date}</th><td>${cmFull(s.started_at).slice(0, 16)}</td></tr></tbody></table>
      ${s.status === "graded" && !comparison ? `<div class="arstats" style="margin:14px 0 0"><div><small>${arLabHasScore(s)?L.total:L.grade}</small><b>${arLabScoreLabel(s)}</b></div>
        ${!s.sample_standing && !reviewOnly && arLabHasScore(s) && s.standing ? `<div><small>${L.pct}</small><b>${s.standing.mine}%</b></div><div><small>HaslaLab · ${L.rank}</small><b>${L.rankV(s.standing.rank, s.standing.n)}</b></div>
        <div><small>${L.top}</small><b>${s.standing.top_pct}%</b></div><div><small>${L.avg} · ${L.max}</small><b>${s.standing.avg}% · ${s.standing.max}%</b></div>` : ""}</div>
        ${!s.sample_standing && !reviewOnly && arLabHasScore(s) && s.standing && !s.standing.first ? `<p class="arempty" style="margin:8px 0 0">${L.retryNote}</p>` : ""}` : ""}
      ${comparison?'<div id="arLabComparison"></div>':''}</div>
    ${s.status === "ended" && !isContest ? `<div class="arpanel"><h3>${L.payH}</h3><p class="arempty" style="margin-top:0">${L.payNote}</p>
      <button class="cmbtn pri" id="arLabPay">${L.payBtn}</button><p class="arinfo" id="arLabPayMsg"></p></div>` : ""}
    ${s.tasks.map((t) => { const x = per[t] || {}, sol = arLabSol(s, t);
      const body = x.status === "graded" && arQualitative(x) ? arLabQualitative(x)
        : x.status === "graded" && Array.isArray(x.items) ? arLabItems(x, s.regulation, s.reviews ? {task: t, list: s.reviews} : null)
        : x.status === "graded" ? arResult({status: "graded", score: x.score, detail: {...x, kind: "essay"}}, {points: x.points})
        : x.status === "pending" ? `<div class="cmnote">${L.why[x.why] || L.st.pending}</div>` : x.status === "error" ? `<div class="cmnote">${L.err}</div>`
        : x.status === "empty" ? `<div class="cmnote">${L.empty}</div>` : `<div class="cmnote">${L.st[s.status] || ""}</div>`;
      return `<div class="arpanel"><h3>${esc(t)} ${x.status ? "· " + (L.st[x.status] || "") : ""} ${sol ? `<a style="float:right;font-weight:500;font-size:13px" href="${esc(sol)}" target="_blank" rel="noopener">${L.sol} ↗</a>` : ""}</h3>${body}</div>`; }).join("")}
    ${s.regulation ? `<div class="arpanel"><details><summary style="cursor:pointer;font-weight:700">${L.regH} <span style="font-weight:400;color:var(--graphite)">${esc(s.regulation.version)}</span></summary>
      <p class="arempty" style="margin:8px 0">${L.regNote}</p><ol class="arreg">${s.regulation.rules.map((r) => `<li><b>${esc(r.id)}</b> ${esc(lang === "en" ? r.en : r.ko)}</li>`).join("")}</ol></details></div>` : ""}
    <div class="arpanel"><h3>${L.pages} · ${s.pages.length}</h3>${s.pages.map((p) => `<details class="arsub"><summary><b>${esc(p.task)}</b> ${p.kind === "answer" ? L.answer : L.working} #${p.no}${p.edited ? " ✎" : ""}</summary>
      <div style="display:grid;grid-template-columns:minmax(0,220px) minmax(0,1fr);gap:12px;margin-top:8px"><div data-img="${p.id}" style="background:#f3f4f6;border-radius:8px;min-height:120px"></div><pre class="aranswer">${esc(p.text)}</pre></div></details>`).join("") || `<p class="arempty">${T.empty}</p>`}
      ${open ? "" : `<p style="margin:12px 0 0"><button class="cmbtn sm" id="arLabDel">${L.del}</button></p>`}</div>`;
  arMath(root);
  if (comparison) window.labComparison.mount(root.querySelector('#arLabComparison'), s, lang, {base:'sim/results/',isCurrent:alive});
  const pay = root.querySelector("#arLabPay");
  if (pay) pay.onclick = async () => {
    pay.disabled = true; pay.textContent = L.payBusy;
    try { await cmApi("POST", `/lab/sessions/${s.id}/pay?lang=${lang}`, {lang,max_cost:arLabCost(s)}); if (alive()) arLabOne(root, alive, id); }
    catch (e) {
      if(!alive())return;
      if(e.code==='price_changed'){
        await arLabOne(root,alive,id);
        const message=root.querySelector('#arLabPayMsg');if(message)message.textContent=lang==='en'?'The fee changed. Check the updated fee and request grading again.':'채점 비용이 갱신되었습니다. 새 비용을 확인한 뒤 다시 신청해 주세요.';
      }else{pay.disabled=false;pay.textContent=L.payBtn;root.querySelector('#arLabPayMsg').textContent=e.code==='no_tokens'?L.payNo:arErr(e);}
    }
  };
  root.querySelectorAll("details.arsub").forEach((d) => d.addEventListener("toggle", async () => {
    const box = d.querySelector("[data-img]"); if (!d.open || !box || box.firstChild) return;
    try { const r = await fetch(cmBase() + `/api/lab/pages/${box.dataset.img}/img`, {headers: {Authorization: "Bearer " + cmTok()}});
      if (r.ok) box.innerHTML = `<img alt="" style="width:100%;border-radius:8px" src="${URL.createObjectURL(await r.blob())}">`;
      else if (r.status === 410) box.innerHTML = `<p class="arempty" style="padding:10px">${L.purged}</p>`; } catch (e) {}
  }));
  if(s.status==='grading')void arWatchLab(root,alive,id,s);
  /* admins: the reference marks for this experiment */
  root.querySelectorAll("[data-rev]").forEach((b) => b.onclick = async () => {
    const panel = b.closest(".arpanel"), items = [...panel.querySelectorAll("[data-ref]")].filter((x) => x.value !== "").map((x) => ({id: x.dataset.ref, ref: +x.value}));
    try { const r = await cmApi("POST", `/admin/lab/${id}/review`, {task: b.dataset.rev, items}); cmToast(T.saved + " · " + r.saved); } catch (e) { cmToast(arErr(e)); }
  });
  const del = root.querySelector("#arLabDel");
  if (del) del.onclick = async () => { if (!confirm(L.delQ)) return; try { await cmApi("DELETE", `/lab/sessions/${id}`); location.hash = "#/lab"; } catch (e) { cmToast(arErr(e)); } };
}
/* what grading costs, how long it takes and how right it is (admins) */
function arLabMetrics(m) {
  const L = lbt(), e = m.per_exam, n = (v, d) => v == null ? "—" : (+v).toLocaleString(undefined, {maximumFractionDigits: d ?? 0}), usd = (v) => v == null ? "—" : "$" + (+v).toFixed(4);
  const a = m.accuracy, st = m.storage || {};
  return `<h4 class="arh4">${L.mH} <small style="font-weight:400;color:var(--graphite)">${L.mDays}</small></h4>
    ${e.n ? `<div class="arstats"><div><small>${L.mExam} · ${L.mUsd}</small><b>${usd(e.avg_usd)}</b></div><div><small>${L.mTok}</small><b>${n(e.avg_in_tok)} / ${n(e.avg_out_tok)}</b></div>
      <div><small>${L.mCalls}</small><b>${n(e.avg_calls, 1)}</b></div><div><small>${L.mTime}</small><b>${e.avg_grade_ms == null ? "—" : n(e.avg_grade_ms / 1000, 1) + " s"}</b></div><div><small>${L.mWait}</small><b>${e.avg_wait_s == null ? "—" : n(e.avg_wait_s) + " s"}</b></div></div>` : `<p class="arempty">${L.mNone}</p>`}
    ${m.steps.length ? `<details class="arsub"><summary>${L.mStep}</summary><table class="cmtbl artbl"><thead><tr><th>step</th><th>model</th><th>n</th><th>in / out / cached</th><th>${L.mUsd}</th><th>ms</th></tr></thead><tbody>
      ${m.steps.map((x) => `<tr><td>${esc(x.step)}</td><td>${esc(x.provider)}:${esc(x.model || "")}</td><td>${x.n}${x.failed ? ` <span style="color:#c0392b">(${x.failed}✗)</span>` : ""}</td><td>${n(x.in_tok)} / ${n(x.out_tok)} / ${n(x.cached_tok)}${x.pages ? ` · ${x.pages}p` : ""}</td><td>${usd(x.usd)}</td><td>${n(x.avg_ms)}</td></tr>`).join("")}</tbody></table></details>` : ""}
    ${m.sessions.length ? `<details class="arsub"><summary>${L.mRecent} (${m.sessions.length})</summary><table class="cmtbl artbl"><tbody>${m.sessions.slice(0, 30).map((x) => `<tr><td><a href="#/lab/${x.id}">#${x.id}</a> ${esc(x.exam_key)}</td><td>${esc(x.status)}${x.score != null ? ` · ${x.score}/${x.points}` : ""}</td><td>${x.pages}p · ${x.calls || 0} calls</td><td>${usd(x.usd)}</td><td>${x.grade_ms == null ? "—" : n(x.grade_ms / 1000, 1) + " s"}</td></tr>`).join("")}</tbody></table></details>` : ""}
    <p style="margin:8px 0 0"><b>${L.mAcc}</b> — ${a.items ? `${L.mItems} ${a.items} · ${L.mMae} ${a.mae} · ${L.mExact} ${a.exact}% · ${L.mTaskDiff} ${a.task_diff_pct ?? "—"}%` : L.mNone}</p>
    <p style="margin:4px 0 0"><b>${L.mStore}</b> — ${n(st.pages)} · D1 ${n((st.d1_bytes || 0) / 1048576, 1)} MB${m.r2 ? ` · R2 ${n(st.in_r2)}` : ""} · ${L.mKeep(m.keep_hours)}${st.purged ? ` · −${n(st.purged)}` : ""}</p>`;
}
async function arLabAdmin(box) {
  const L = lbt();
  let q; try { q = await cmApi("GET", "/admin/lab/queue"); } catch (e) { box.remove(); return; }
  const mx = await cmApi("GET", "/admin/lab/metrics?days=30").catch(() => null);
  box.innerHTML = `<h3>⏱ ${L.admin}</h3>${mx ? arLabMetrics(mx) : ""}
    <h4 class="arh4">${L.grantH}</h4>
    <form class="arq" id="lbTok"><input name="u" placeholder="${L.user}"><input name="d" type="number" step="0.1" placeholder="${L.delta}" style="width:120px"><input name="n" placeholder="note">
      <button class="cmbtn sm pri">${T0(L.grantH)}</button><button class="cmbtn sm" type="button" data-look>${L.look}</button><span class="arinfo"></span></form>
    <h4 class="arh4">${L.rubH}</h4>
    <form id="lbRub" class="arpf"><label>exam_key<input name="exam_key" placeholder="ipho2024"></label><label>task<input name="task" placeholder="E1"></label><label>${L.points}<input name="points" type="number" step="0.1" placeholder="10"></label>
      <label>rubric<textarea name="rubric" rows="5" placeholder='[{"id":"A.1","name":"R0","max":0.5,"requirement":"R0 = 108 ± 2 Ω","partial":"…"}]'></textarea></label>
      <label>reference<textarea name="reference" rows="4" placeholder="official answers, tolerances"></textarea></label>
      <button class="cmbtn sm" type="button" data-load>${L.load}</button> <button class="cmbtn pri" type="submit">${arT().save}</button><span class="arinfo"></span></form>
    <h4 class="arh4">${L.queue} (${q.sessions.length})</h4>${q.sessions.map((x) => `<details class="arsub"><summary><b>#${x.id}</b> ${esc(x.exam_key.toUpperCase())} · ${esc(x.nickname)} · ${esc(x.status)} · ${x.n_pages}p</summary>
      <p><a href="#/lab/${x.id}">#/lab/${x.id}</a></p>${x.tasks.map((t) => { const d = (x.detail && x.detail.tasks || {})[t] || {};
        return `<form class="arq" data-lab="${x.id}" data-task="${esc(t)}"><b>${esc(t)}</b> <span>${esc(d.status || "")}${d.why ? " (" + esc(d.why) + ")" : ""}</span>
          <input name="score" type="number" step="0.1" min="0" placeholder="score" style="width:90px"><input name="points" type="number" step="0.1" value="${d.points || 10}" style="width:80px" title="${L.points}"><input name="note" placeholder="note">
          <button class="cmbtn sm pri" type="submit">${L.give}</button><button class="cmbtn sm" type="button" data-re>${L.regrade}</button></form>`; }).join("")}</details>`).join("") || `<p class="arempty">${arT().empty}</p>`}`;
  function T0(x) { return lang === "en" ? "Apply" : "적용"; }
  const tf = box.querySelector("#lbTok"), info = tf.querySelector(".arinfo");
  tf.onsubmit = async (e) => { e.preventDefault(); try { const r = await cmApi("POST", "/admin/lab/tokens", {user: tf.u.value.trim(), delta: +tf.d.value, note: tf.n.value}); info.textContent = "→ " + r.tokens; } catch (er) { info.textContent = arErr(er); } };
  tf.querySelector("[data-look]").onclick = async () => { try { const r = await cmApi("GET", "/admin/lab/tokens?user=" + encodeURIComponent(tf.u.value.trim())); info.textContent = `${r.user.nickname} (@${r.user.username}): ${r.user.exam_tokens} · ` + r.ledger.slice(0, 5).map((l) => (l.delta > 0 ? "+" : "") + l.delta + " " + l.reason).join(", "); } catch (er) { info.textContent = arErr(er); } };
  const rf = box.querySelector("#lbRub"), ri = rf.querySelector(".arinfo");
  rf.querySelector("[data-load]").onclick = async () => { try { const r = await cmApi("GET", "/admin/lab/rubrics?key=" + encodeURIComponent(rf.exam_key.value.trim()));
    const x = r.rubrics.find((y) => y.task === rf.task.value.trim()) || r.rubrics[0]; if (!x) { ri.textContent = "—"; return; }
    rf.task.value = x.task; rf.points.value = x.points; rf.rubric.value = JSON.stringify(JSON.parse(x.rubric), null, 1); rf.reference.value = x.reference || ""; ri.textContent = r.rubrics.map((y) => y.task).join(", "); } catch (er) { ri.textContent = arErr(er); } };
  rf.onsubmit = async (e) => { e.preventDefault(); try { await cmApi("POST", "/admin/lab/rubrics", {exam_key: rf.exam_key.value.trim(), task: rf.task.value.trim(), points: +rf.points.value, rubric: rf.rubric.value, reference: rf.reference.value}); ri.textContent = arT().saved; } catch (er) { ri.textContent = arErr(er); } };
  for (const f of box.querySelectorAll("[data-lab]")) {
    const send = async (b) => { try { await cmApi("POST", `/admin/lab/${f.dataset.lab}`, {task: f.dataset.task, ...b}); arLabAdmin(box); } catch (er) { cmToast(arErr(er)); } };
    f.onsubmit = (e) => { e.preventDefault(); send({score: +f.score.value, points: +f.points.value, note: f.note.value}); };
    f.querySelector("[data-re]").onclick = () => send({regrade: true});
  }
}

/* ── admin ── */
async function arAdmin(root, alive) {
  const T = arT(), [pj, qj] = await Promise.all([cmApi("GET", "/admin/problems"), cmApi("GET", "/admin/queue")]); if (!alive()) return;
  const F = ["id", "week", "no", "kind", "subject", "level", "points", "title_ko", "title_en", "body_ko", "body_en", "unit", "answer", "rubric", "model_ko", "model_en", "source", "opens_at", "closes_at"];
  const big = ["body_ko", "body_en", "rubric", "model_ko", "model_en"];
  root.innerHTML = `
    <div class="cmtop"><div><h1>${T.admin}</h1></div>${arModelTestLink()}</div>
    <div class="arpanel"><h3>${T.queue} (${qj.subs.length})</h3>${qj.subs.map((s) => `
      <details class="arsub"><summary><b>#${s.id}</b> ${esc(s.title_ko)} · ${esc(s.nickname)} · ${esc(s.status)}</summary><pre class="aranswer">${esc(s.answer)}</pre>
        <pre class="aranswer small">${esc(s.rubric || "")}</pre>
        <form class="arq" data-id="${s.id}"><input name="score" type="number" min="0" max="${s.points}" placeholder="0–${s.points}"><input name="note" placeholder="note">
          <button class="cmbtn sm pri" type="submit">${T.giveScore}</button><button class="cmbtn sm" type="button" data-re="1">${T.regrade}</button></form></details>`).join("") || `<p class="arempty">${T.empty}</p>`}</div>
    <div class="arpanel"><h3>${T.addP}</h3>
      <select id="arPick" class="cmsel"><option value="">— new —</option>${pj.problems.map((x) => `<option value="${x.id}">${esc(arPeriodLabel(x))} #${x.no} ${esc(x.title_ko)}</option>`).join("")}</select>
      <form id="arPF" class="arpf">${F.map((k) => big.includes(k) ? `<label>${k}<textarea name="${k}" rows="4"></textarea></label>` : `<label>${k === "week" ? (lang === "ko" ? "월 (YYYY-MM)" : "Month (YYYY-MM)") : k}<input name="${k}"${k === "week" ? ' placeholder="2026-11"' : ""}></label>`).join("")}
        <p class="arempty">answer (short): {"value":1.79,"rel":0.005} or {"value":5.19,"abs":0.02} · rubric (essay): [{"id":"A","name":"…","max":25,"requirement":"…","partial":"…"}] · level: 1–30 (Bronze V = 1 … Bronze I = 5, Silver V = 6 … Ruby I = 30) · opens_at/closes_at: unix seconds</p>
        <button class="cmbtn pri" type="submit">${T.save}</button><span class="arinfo"></span></form></div>
    <div class="arpanel" id="arLabAdm"></div>`;
  if ((ar.health || {}).lab) arLabAdmin(root.querySelector("#arLabAdm")); else root.querySelector("#arLabAdm").remove();
  const pf = root.querySelector("#arPF");
  root.querySelector("#arPick").onchange = (e) => { const x = pj.problems.find((y) => y.id == e.target.value) || {}; for (const k of F) pf[k].value = x[k] == null ? "" : x[k]; };
  pf.onsubmit = async (e) => { e.preventDefault(); const d = {}; for (const k of F) d[k] = pf[k].value;
    for (const k of ["no", "level", "points", "opens_at", "closes_at"]) d[k] = d[k] === "" ? undefined : +d[k];
    try { const r = await cmApi("POST", "/admin/problems", d); pf.id.value = r.id; pf.querySelector(".arinfo").textContent = T.saved + " #" + r.id; } catch (er) { pf.querySelector(".arinfo").textContent = arErr(er); } };
  for (const q of root.querySelectorAll(".arq")) {
    const send = async (b) => { try { await cmApi("POST", `/admin/submissions/${q.dataset.id}`, b); arAdmin(root, alive); } catch (er) { cmToast(arErr(er)); } };
    q.onsubmit = (e) => { e.preventDefault(); send({score: q.score.value, note: q.note.value}); };
    q.querySelector("[data-re]").onclick = () => send({regrade: true, lang});
  }
}

/* Developer-only provider comparison. It does not create an exam or submit marks. */
async function arServerGuide(root, alive) {
  const english = lang === "en", T = english ? {
    denied: "The operations guide is available to developer accounts.", login: "Sign in", retry: "Try again", failed: "Unable to load the operations guide."
  } : {denied: "개발자 계정만 운영 가이드를 열 수 있습니다.", login: "로그인", retry: "다시 시도", failed: "운영 가이드를 불러오지 못했습니다."};
  if (!alive()) return;
  const denied = () => {
    if (!cm.me) try { sessionStorage.setItem("hlCmBack", "#/lab/server-guide"); } catch (_) {}
    root.innerHTML = `<div class="cmnote">${T.denied}${!cm.me ? ` <a class="cmbtn sm" href="#/login">${T.login}</a>` : ""}</div>`;
  };
  if (!cmTok()) { denied(); return; }
  try {
    // Revalidate against primary before downloading the developer-only UI.
    // The guide contains no credentials; the server role remains authoritative.
    const identity = await cmApi("GET", "/me", undefined, {forcePrimary:true});
    if (!alive()) return;
    cm.me = identity.user || null; cm.meChecked = true;
    if (cm.me?.role !== "admin") { denied(); return; }
    await siteDataLoader.load("developer-guide");
    if (!alive() || cm.me?.role !== "admin") return;
    ar.poller = window.HL_SERVER_GUIDE.mount(root, {language:lang, apiBase:cmBase(), alive:() => alive() && cm.me?.role === "admin"});
  } catch (_) {
    if (!alive()) return;
    root.innerHTML = `<div class="cmnote">${T.failed} <button type="button" class="cmbtn sm" data-retry-server-guide>${T.retry}</button></div>`;
    root.querySelector("[data-retry-server-guide]").onclick = () => arServerGuide(root, alive);
  }
}

const AR_MODEL_PIPELINES = ["gemini-gemini", "gemini-deepseek", "deepseek-deepseek"];
function arModelTestLabels() {
  return lang === "en" ? {
    title: "Developer model test", link: "Model test · developer", back: "My exams",
    intro: "Compare OCR and grading on the same answer pages.",
    separate: "These test results do not enter learning records or rankings and do not use exam tokens.",
    denied: "This test is available only to developer accounts.", login: "Sign in", retry: "Try again",
    problem: "Problem statement", rubric: "Reference answer and marking criteria", points: "Full marks",
    images: "Answer images", imageHint: n => `Choose up to ${n} JPEG, PNG or WebP images, in page order.`,
    choice: "OCR and grading combination", run: "Run selected test", preparing: "Preparing images…", running: "Running OCR and grading…",
    empty: "Run another combination with the same inputs to compare the results here.",
    unavailable: "Not connected", ocr: "OCR", grading: "Grading", text: "Recognized answer", uncertain: "Check the transcription",
    feedback: "Grading feedback", review: "Needs review · no final score", incomplete: "Grading incomplete", testIncomplete: "Test incomplete", elapsed: "Total time", usage: "API usage", partialUsage: "Known API usage · partial total",
    totalCost: "Estimated total · USD", costRange: "Estimated range · USD", partialCost: "Known subtotal · USD", unknown: "Unconfirmed", totalUnknown: "Final total unconfirmed",
    totalTokens: "Total tokens", knownTokens: "Known tokens", details: "Stage timing, tokens and prices", requestedModel: "Requested model", resolvedModel: "Response model",
    started: "Started", finished: "Finished", latency: "Response time", tokenRate: "Output tokens/s · reference", inputAll: "Input · includes cache", uncached: "Uncached input", cacheInput: "Cached input", outputAll: "Output · includes thinking", thinking: "Thinking · part of output",
    item: "Billing item", unitPrice: "Price · USD", itemCost: "Estimated cost · USD", perMillion: "per 1M tokens", perToken: "per token", subtotal: "Stage subtotal", priceSource: "Official prices", checked: "Checked",
    pricingNote: "Estimated from public paid Standard token prices; your actual bill may differ.", accountingNote: "Cached input is part of input; thinking tokens are part of output. They are not added twice to totals or costs.", speedNote: "Output tokens/s uses the full request response time and is only a reference.", noOcrResult: "No OCR result was returned.",
    calls: "API calls", input: "input", output: "output", cached: "cached", seconds: "s",
    failed: "The test could not be completed.", geminiOff: "Gemini is not connected.", deepseekOff: "DeepSeek is not connected.",
    badPipeline: "Choose one of the available combinations.", badProblem: "Enter a problem statement within the text limit.",
    badRubric: "Enter the reference answer and marking criteria within the text limit.", badPoints: "Check the full-mark value.",
    badImages: "Choose valid answer images.", tooMany: n => `Choose at most ${n} images.`, tooLarge: "An image is too large to send clearly. Choose a smaller original.",
    auth: "The model provider rejected its API credentials.", limited: "The request limit was reached. Try again later.",
    model: "The configured model is unavailable for this test.", timeout: "The model test timed out. Try again.",
    invalid: "The model did not return a valid result.", noText: "No answer text could be read from the images.",
    network: "The server could not be reached. Check the connection and try again.",
    pipeline: ["1. Gemini OCR + Gemini grading", "2. Gemini OCR + DeepSeek grading", "3. DeepSeek OCR + DeepSeek grading"]
  } : {
    title: "개발자 모델 테스트", link: "모델 테스트 · 개발자", back: "내 시험",
    intro: "같은 답안으로 OCR·채점 조합을 비교합니다.",
    separate: "테스트 결과는 학습 기록·랭킹에 반영되지 않으며 실전 토큰을 사용하지 않습니다.",
    denied: "개발자 계정만 사용할 수 있는 테스트입니다.", login: "로그인", retry: "다시 시도",
    problem: "문제", rubric: "기준 정답·채점 기준", points: "만점",
    images: "답안 사진", imageHint: n => `JPEG·PNG·WebP 사진을 쪽 순서대로 최대 ${n}장 선택하세요.`,
    choice: "OCR·채점 조합", run: "선택한 조합 테스트", preparing: "사진을 준비하고 있습니다…", running: "OCR·채점을 실행하고 있습니다…",
    empty: "같은 입력으로 다른 조합도 실행하면 결과를 나란히 비교할 수 있습니다.",
    unavailable: "연결 안 됨", ocr: "OCR", grading: "채점", text: "OCR 원문", uncertain: "판독 확인",
    feedback: "채점 피드백", review: "검토 필요 · 점수 미확정", incomplete: "채점 미완료", testIncomplete: "테스트 미완료", elapsed: "전체 시간", usage: "API 사용량", partialUsage: "확인된 API 사용량 · 부분 집계",
    totalCost: "예상 총비용 · USD", costRange: "예상 비용 범위 · USD", partialCost: "확인된 부분합 · USD", unknown: "미확정", totalUnknown: "총액 미확정",
    totalTokens: "총 토큰", knownTokens: "확인된 토큰", details: "단계별 시간·토큰·단가", requestedModel: "요청 모델", resolvedModel: "응답 모델",
    started: "시작", finished: "종료", latency: "응답 시간", tokenRate: "출력 토큰/초 · 참고", inputAll: "입력 · 캐시 포함", uncached: "비캐시 입력", cacheInput: "캐시 입력", outputAll: "출력 · 생각 포함", thinking: "생각 · 출력의 일부",
    item: "비용 항목", unitPrice: "단가 · USD", itemCost: "예상 비용 · USD", perMillion: "100만 토큰당", perToken: "1토큰당", subtotal: "단계 합계", priceSource: "공식 단가", checked: "확인일",
    pricingNote: "유료 Standard 공개 단가 기준 예상비용이며 실제 청구액과 다를 수 있습니다.", accountingNote: "캐시 입력은 입력에, 생각 토큰은 출력에 포함됩니다. 합계·비용에 다시 더하지 않습니다.", speedNote: "출력 토큰/초는 요청 전체 응답시간 기준 참고값입니다.", noOcrResult: "반환된 OCR 결과가 없습니다.",
    calls: "API 호출수", input: "입력", output: "출력", cached: "캐시", seconds: "초",
    failed: "테스트를 완료하지 못했습니다.", geminiOff: "Gemini가 연결되지 않았습니다.", deepseekOff: "DeepSeek가 연결되지 않았습니다.",
    badPipeline: "사용할 수 있는 조합을 선택하세요.", badProblem: "문제를 글자 수 제한 안에서 입력하세요.",
    badRubric: "기준 정답·채점 기준을 글자 수 제한 안에서 입력하세요.", badPoints: "만점을 확인하세요.",
    badImages: "올바른 답안 사진을 선택하세요.", tooMany: n => `사진을 최대 ${n}장 선택하세요.`, tooLarge: "사진을 선명하게 전송하기에는 용량이 큽니다. 더 작은 원본을 선택하세요.",
    auth: "모델 제공업체가 API 인증을 거부했습니다.", limited: "요청 한도에 도달했습니다. 잠시 후 다시 시도하세요.",
    model: "설정된 모델로 이 테스트를 실행할 수 없습니다.", timeout: "모델 테스트 응답 시간이 초과됐습니다. 다시 시도하세요.",
    invalid: "모델이 올바른 결과를 반환하지 않았습니다.", noText: "사진에서 답안 글씨를 읽지 못했습니다.",
    network: "서버에 연결하지 못했습니다. 연결 상태를 확인한 뒤 다시 시도하세요.",
    pipeline: ["1. Gemini OCR + Gemini 채점", "2. Gemini OCR + DeepSeek 채점", "3. DeepSeek OCR + DeepSeek 채점"]
  };
}
function arModelTestLink(active) {
  if (cm.me?.role !== "admin") return "";
  const english = lang === "en";
  return `<nav aria-label="${english ? "Developer tools" : "개발자 도구"}" style="display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 16px">
    <a class="cmbtn sm" href="#/lab/model-test" ${active === "model-test" ? 'aria-current="page"' : ""}>${arModelTestLabels().link}</a>
    <a class="cmbtn sm" href="#/lab/server-guide" ${active === "server-guide" ? 'aria-current="page"' : ""}>${english ? "Server & operations guide" : "서버 구조·운영 가이드"}</a></nav>`;
}
function arModelTestError(error, T, maxImages = 3) {
  const code = String(error?.code || error?.error || ""), messages = {
    gemini_not_configured: T.geminiOff, deepseek_not_configured: T.deepseekOff,
    model_test_bad_pipeline: T.badPipeline, model_test_bad_problem: T.badProblem,
    model_test_bad_rubric: T.badRubric, model_test_bad_points: T.badPoints,
    model_test_bad_images: T.badImages, model_test_bad_image: T.badImages, bad_image: T.badImages,
    model_test_too_many_images: T.tooMany(maxImages), model_test_image_too_large: T.tooLarge, image_too_big: T.tooLarge,
    model_test_provider_auth: T.auth, model_test_provider_rate_limited: T.limited, rate_limited: T.limited,
    model_test_model_unavailable: T.model, model_test_ocr_model_unsupported: T.model, model_test_invalid_config: T.model,
    model_test_timeout: T.timeout, model_test_invalid_response: T.invalid, model_test_ocr_empty: T.noText,
    forbidden: T.denied, login_required: T.denied, network: T.network
  };
  const stage = error?.stage === "ocr" ? T.ocr : error?.stage === "grading" || error?.stage === "grade" ? T.grading : "";
  const model = [error?.provider, error?.model].filter(x => typeof x === "string" && x).join(" · ");
  return [stage, model, messages[code] || T.failed].filter(Boolean).join(" · ");
}
const arModelTestKnown = n => Number.isFinite(n) && n >= 0;
function arModelTestNumber(n, T, digits = 3) {
  return arModelTestKnown(n) ? n.toLocaleString(lang === "en" ? "en" : "ko", {maximumFractionDigits:digits}) : T.unknown;
}
function arModelTestUsd(n, T) {
  if (!arModelTestKnown(n)) return T.unknown;
  const value = Number(n.toPrecision(6)).toLocaleString("en-US", {maximumFractionDigits:12,useGrouping:false});
  return "$" + (n > 0 && Number(value) === 0 ? n.toExponential(4) : value);
}
function arModelTestMoneyRange(range, T) {
  if (!range || !arModelTestKnown(range.min) || !arModelTestKnown(range.max) || range.min > range.max) return T.unknown;
  return arModelTestUsd(range.min, T) + (range.min === range.max ? "" : " – " + arModelTestUsd(range.max, T));
}
function arModelTestPriceSummary(pricing, T) {
  const p = pricing || {};
  if (p.incomplete || p.status === "incomplete") return {label:T.partialCost,
    value:p.priced_calls > 0 ? (p.known_range_usd ? arModelTestMoneyRange(p.known_range_usd, T) : arModelTestUsd(p.known_usd, T)) : T.unknown,
    note:T.totalUnknown};
  if (p.status === "estimated") return {label:T.totalCost,value:arModelTestUsd(p.total_usd, T),note:""};
  if (p.status === "range") return {label:T.costRange,value:arModelTestMoneyRange(p.range_usd, T),note:""};
  return {label:T.totalCost,value:T.unknown,note:T.totalUnknown};
}
function arModelTestPriceLink(value) {
  try {
    if (typeof value !== "string" || value.length > 2048) return "";
    const url = new URL(value);
    if (url.protocol !== "https:" || !["ai.google.dev", "api-docs.deepseek.com"].includes(url.hostname) || url.username || url.password || (url.port && url.port !== "443")) return "";
    return url.href;
  } catch (_) { return ""; }
}
function arModelTestStage(stage, T) {
  const p = stage.pricing || {}, price = arModelTestPriceSummary(p, T);
  const phase = stage.stage === "ocr" ? T.ocr : stage.stage === "grading" ? T.grading : String(stage.stage || T.unknown);
  const provider = ({gemini:"Gemini",deepseek:"DeepSeek"})[stage.provider] || stage.provider || T.unknown;
  const time = arModelTestKnown(stage.ms) ? arModelTestNumber(stage.ms / 1000, T) + T.seconds + " · " + arModelTestNumber(stage.ms, T) + " ms" : T.unknown;
  const pairs = [
    [T.requestedModel, stage.model || T.unknown], [T.resolvedModel, stage.resolved_model || T.unknown],
    [T.started + " · UTC", stage.started_at || T.unknown], [T.finished + " · UTC", stage.finished_at || T.unknown],
    [T.calls, arModelTestNumber(stage.calls, T)], [T.latency, time], [T.tokenRate, arModelTestNumber(stage.output_tokens_per_second, T, 2)]
  ];
  const tokens = [[T.inputAll,stage.input_tokens],[T.uncached,stage.uncached_input_tokens],[T.cacheInput,stage.cached_tokens],
    [T.outputAll,stage.output_tokens],[T.thinking,stage.reasoning_tokens],[T.totalTokens,stage.total_tokens]];
  const rate = (key, unit) => {
    const fixed = p["unit_prices_per_" + unit]?.[key], ranges = p["unit_price_ranges_per_" + unit];
    return arModelTestKnown(fixed) ? arModelTestUsd(fixed, T) : arModelTestMoneyRange(ranges && {min:ranges.min?.[key],max:ranges.max?.[key]}, T);
  };
  const component = key => arModelTestKnown(p.components_usd?.[key]) ? arModelTestUsd(p.components_usd[key], T) :
    arModelTestMoneyRange(p.component_ranges_usd && {min:p.component_ranges_usd.min?.[key],max:p.component_ranges_usd.max?.[key]}, T);
  const source = arModelTestPriceLink(p.source_url);
  return `<section style="margin:18px 0;padding:14px;border:1px solid var(--line);border-radius:10px;min-width:0;overflow-wrap:anywhere">
    <h4 class="arh4" style="margin-top:0">${esc(phase)} · ${esc(provider)}</h4>
    <dl style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.5fr);gap:6px 14px;margin:0 0 14px;font-size:.84rem">
      ${pairs.map(([label,value]) => `<dt style="word-break:keep-all">${esc(label)}</dt><dd style="margin:0;min-width:0;overflow-wrap:anywhere">${esc(value)}</dd>`).join("")}</dl>
    <table class="cmtbl artbl" style="table-layout:fixed;width:100%;margin-bottom:14px;word-break:keep-all"><tbody>${tokens.map(([label,value]) => `<tr><th style="width:60%;text-align:left;overflow-wrap:anywhere">${esc(label)}</th><td style="display:table-cell;white-space:normal;overflow-wrap:anywhere;text-overflow:clip">${esc(arModelTestNumber(value,T))}</td></tr>`).join("")}</tbody></table>
    <table class="cmtbl artbl" style="table-layout:fixed;width:100%;font-size:.79rem;overflow-wrap:anywhere;word-break:keep-all"><thead style="display:table-header-group"><tr><th style="width:27%">${T.item}</th><th style="width:43%">${T.unitPrice}</th><th style="width:30%">${T.itemCost}</th></tr></thead><tbody>
      ${[["input_uncached",T.uncached],["input_cached",T.cacheInput],["output",T.outputAll]].map(([key,label]) => `<tr><td style="display:table-cell;white-space:normal;overflow-wrap:anywhere;text-overflow:clip">${esc(label)}<small style="display:block">${esc(arModelTestNumber(p.billing_tokens?.[key],T))}</small></td>
        <td style="display:table-cell;white-space:normal;overflow-wrap:anywhere;text-overflow:clip">${esc(rate(key,"million"))}<small style="display:block">${T.perMillion}</small>${esc(rate(key,"token"))}<small style="display:block">${T.perToken}</small></td><td style="display:table-cell;white-space:normal;overflow-wrap:anywhere;text-overflow:clip">${esc(component(key))}</td></tr>`).join("")}
      <tr><th colspan="2" style="text-align:left">${T.subtotal}</th><td style="display:table-cell;white-space:normal;overflow-wrap:anywhere;text-overflow:clip"><b>${esc(price.value)}</b></td></tr></tbody></table>
    ${source ? `<p class="arnote" style="margin-bottom:0"><a href="${esc(source)}" target="_blank" rel="noopener noreferrer">${T.priceSource}</a> · ${T.checked} ${esc(p.checked_at || T.unknown)}</p>` : ""}
  </section>`;
}
function arModelTestResult(result, T) {
  const index = AR_MODEL_PIPELINES.indexOf(typeof result.pipeline === "string" ? result.pipeline : result.pipeline?.id);
  const o = result.ocr || {}, g = result.grading || {}, u = result.usage || {}, stages = Array.isArray(u.stages) ? u.stages : [];
  const time = n => arModelTestKnown(n) ? arModelTestNumber(n / 1000,T) + T.seconds : T.unknown;
  const price = arModelTestPriceSummary(u.pricing,T), knownTokens = arModelTestKnown(u.known_tokens?.total_tokens);
  const partialTokens = !arModelTestKnown(u.total_tokens) && u.incomplete && knownTokens;
  const stat = (label,value,note = "") => `<div style="min-width:0;overflow-wrap:anywhere"><small>${esc(label)}</small><b style="display:block;font-size:clamp(16px,3vw,22px);overflow-wrap:anywhere">${esc(value)}</b>${note ? `<small style="display:block;overflow-wrap:anywhere">${esc(note)}</small>` : ""}</div>`;
  const scored = g.status === "graded" && Number.isFinite(g.score) && Number.isFinite(g.points);
  return `<article class="arpanel" data-model-result="${esc(AR_MODEL_PIPELINES[index] || "")}" style="min-width:0;overflow-wrap:anywhere">
    <h3>${esc(T.pipeline[index] || T.title)}</h3>
    <div class="arstats" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,150px),1fr));gap:12px">
      ${stat(price.label,price.value,price.note)}${stat(T.elapsed,time(result.elapsed_ms))}
      ${stat(T.ocr,time(o.ms),[o.provider,o.model].filter(Boolean).join(" · "))}${stat(T.grading,time(g.ms),[g.provider,g.model].filter(Boolean).join(" · "))}
      ${stat(partialTokens ? T.knownTokens : T.totalTokens,partialTokens ? arModelTestNumber(u.known_tokens.total_tokens,T) + " + ?" : arModelTestNumber(u.total_tokens,T))}${stat(T.calls,arModelTestNumber(u.calls,T))}</div>
    ${result.failure ? `<p class="arinfo bad">${esc(result.failure)}</p>` : ""}
    <div class="arres${scored ? " ok" : ""}"><b>${T.grading}</b><span>${scored ? arModelTestNumber(g.score,T) + " / " + arModelTestNumber(g.points,T) : result.failure ? (result.failureStage === "ocr" ? T.testIncomplete : T.incomplete) : T.review}</span></div>
    ${g.feedback ? `<h4 class="arh4">${T.feedback}</h4><p style="white-space:pre-wrap">${esc(g.feedback)}</p>` : ""}
    <details open><summary>${T.text}</summary><pre class="aranswer">${esc(o.text || T.noOcrResult)}</pre></details>
    ${(o.uncertainties || []).length ? `<h4 class="arh4">${T.uncertain}</h4><ul>${o.uncertainties.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
    <details style="margin-top:16px" data-model-metrics><summary style="font-weight:700;cursor:pointer">${T.details}</summary>
      ${stages.map(stage => arModelTestStage(stage,T)).join("") || `<p class="arnote">${T.unknown}</p>`}
      <p class="arnote">${T.accountingNote}<br>${T.speedNote}</p></details>
    <p class="arnote">${T.pricingNote}</p>
  </article>`;
}
async function arModelTest(root, alive) {
  const T = arModelTestLabels();
  if (!alive()) return;
  if (cm.me?.role !== "admin") {
    if (!cm.me) try { sessionStorage.setItem("hlCmBack", "#/lab/model-test"); } catch (_) {}
    root.innerHTML = `<div class="cmnote">${T.denied}${!cm.me ? ` <a class="cmbtn sm" href="#/login">${T.login}</a>` : ""}</div>`;
    return;
  }
  let config;
  try { config = await cmApi("GET", "/admin/lab/model-test"); }
  catch (error) {
    if (!alive()) return;
    root.innerHTML = `<div class="cmnote">${esc(arModelTestError(error, T))} <button class="cmbtn sm" data-retry-model-test>${T.retry}</button></div>`;
    root.querySelector("[data-retry-model-test]").onclick = () => arModelTest(root, alive);
    return;
  }
  if (!alive() || cm.me?.role !== "admin") return;
  const limits = { maxImages: 3, maxImageBytes: 1900000, maxTotalImageBytes: 5700000, maxText: 12000, maxRubric: 20000, maxPoints: 1000, ...config.limits };
  const pipelines = AR_MODEL_PIPELINES.map(id => (config.pipelines || []).find(x => x.id === id) || { id, available: false });
  const first = pipelines.find(x => x.available === true)?.id;
  root.innerHTML = `<div class="cmtop"><div><h1>${T.title}</h1><p>${T.intro}</p></div><a class="cmbtn sm" href="#/lab">${T.back}</a></div>
    ${arModelTestLink("model-test")}
    <p class="arnote">${T.separate}</p>
    <form id="arModelTestForm"><fieldset style="border:0;padding:0;margin:0;min-width:0">
      <div class="arpanel"><h3>${T.choice}</h3>${pipelines.map((p, i) => `<label style="display:flex;align-items:flex-start;gap:10px;margin:14px 0">
        <input type="radio" name="pipeline" value="${p.id}" ${p.id === first ? "checked" : ""} ${p.available === true ? "" : "disabled"} style="margin-top:5px">
        <span><b>${T.pipeline[i]}</b><small class="arnote" style="display:block">${p.available === true ? esc([p.ocr?.model, p.grading?.model].filter(Boolean).join(" → ")) : esc(p.reason ? arModelTestError({code:p.reason}, T, limits.maxImages) : T.unavailable)}</small></span></label>`).join("")}</div>
      <div class="arpanel arpf"><label>${T.problem}<textarea name="problem" rows="5" required maxlength="${limits.maxText}"></textarea></label>
        <label>${T.rubric}<textarea name="rubric" rows="5" required maxlength="${limits.maxRubric}"></textarea></label>
        <label>${T.points}<input name="points" type="number" min="0.01" max="${limits.maxPoints}" step="any" value="10" required></label>
        <label>${T.images}<input name="images" type="file" accept="image/jpeg,image/png,image/webp" multiple required><small class="arnote">${T.imageHint(limits.maxImages)}</small></label></div>
      <div id="arModelPhotos" style="display:flex;gap:12px;flex-wrap:wrap;margin:14px 0"></div>
      <button class="cmbtn pri" type="submit" ${first ? "" : "disabled"}>${T.run}</button>
    </fieldset></form><p id="arModelStatus" class="arinfo" role="status" aria-live="polite"></p>
    <p id="arModelEmpty" class="arnote">${T.empty}</p><div id="arModelResults"></div>`;
  const form = root.querySelector("#arModelTestForm"), controls = form.querySelector("fieldset"), status = root.querySelector("#arModelStatus");
  const field = name => form.elements.namedItem(name), results = new Map(), urls = new Set();
  let busy = false, disposed = false, controller = null;
  const current = () => !disposed && alive() && cm.me?.role === "admin";
  const paintResults = () => {
    root.querySelector("#arModelResults").innerHTML = AR_MODEL_PIPELINES.map(id => results.has(id) ? arModelTestResult(results.get(id), T) : "").join("");
    root.querySelector("#arModelEmpty").hidden = results.size > 0;
  };
  const clearResults = () => { results.clear(); paintResults(); status.textContent = ""; };
  const revoke = () => { for (const url of urls) URL.revokeObjectURL(url); urls.clear(); };
  const dispose = () => { disposed = true; controller?.abort(); revoke(); window.removeEventListener("hashchange", dispose); window.removeEventListener("pagehide", dispose); };
  window.addEventListener("hashchange", dispose); window.addEventListener("pagehide", dispose);
  form.addEventListener("input", event => { if (current() && !busy && event.target.name !== "pipeline") clearResults(); });
  field("images").onchange = () => {
    if (!current()) return;
    revoke(); clearResults();
    const box = root.querySelector("#arModelPhotos"); box.innerHTML = "";
    for (const file of Array.from(field("images").files || []).slice(0, limits.maxImages)) {
      const url = URL.createObjectURL(file); urls.add(url);
      box.innerHTML += `<figure style="margin:0;max-width:150px"><img src="${esc(url)}" alt="${esc(file.name)}" style="width:120px;height:150px;object-fit:contain;border:1px solid var(--line)"><figcaption class="arnote" style="overflow-wrap:anywhere">${esc(file.name)}</figcaption></figure>`;
    }
  };
  form.onsubmit = async event => {
    event.preventDefault(); if (busy || !current()) return;
    const pipeline = field("pipeline").value, problem = field("problem").value.trim(), rubric = field("rubric").value.trim(), points = Number(field("points").value);
    const files = Array.from(field("images").files || []);
    const fail = code => { status.className = "arinfo bad"; status.textContent = arModelTestError({code}, T, limits.maxImages); };
    if (!pipelines.some(p => p.id === pipeline && p.available === true)) return fail("model_test_bad_pipeline");
    if (!problem || problem.length > limits.maxText) return fail("model_test_bad_problem");
    if (!rubric || rubric.length > limits.maxRubric) return fail("model_test_bad_rubric");
    if (!Number.isFinite(points) || points <= 0 || points > limits.maxPoints) return fail("model_test_bad_points");
    if (!files.length) return fail("model_test_bad_images");
    if (files.length > limits.maxImages) return fail("model_test_too_many_images");
    busy = true; controls.disabled = true; status.className = "arinfo"; status.textContent = T.preparing;
    let timeout, timedOut = false;
    try {
      const scanner = await arLoadScanner(), images = [];
      for (const file of files) {
        if (!current()) return;
        if (file.type && !["image/jpeg", "image/png", "image/webp"].includes(file.type)) throw {code:"model_test_bad_image"};
        const blob = await scanner.encodeUpload(file, {maxBytes:limits.maxImageBytes});
        if (!current()) return;
        if (!["image/jpeg", "image/png", "image/webp"].includes(blob.type)) throw {code:"model_test_bad_image"};
        const bytes = new Uint8Array(await blob.arrayBuffer());
        if (bytes.length > limits.maxImageBytes) throw {code:"model_test_image_too_large"};
        let raw = ""; for (let n = 0; n < bytes.length; n += 32768) raw += String.fromCharCode(...bytes.subarray(n, n + 32768));
        images.push({mime:blob.type,data:btoa(raw)});
      }
      if (!current()) return;
      status.textContent = T.running; controller = new AbortController();
      timeout = setTimeout(() => { timedOut = true; controller?.abort(); }, 150000);
      let response;
      try { response = await fetch(cmBase() + "/api/admin/lab/model-test", {method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer " + cmTok()},body:JSON.stringify({pipeline,problem,rubric,points,images,lang}),signal:controller.signal}); }
      catch (error) { throw {code:timedOut ? "model_test_timeout" : "network"}; }
      const result = await response.json().catch(() => ({error:"model_test_invalid_response"}));
      if (!current()) return;
      if (!response.ok || result.error) throw {...result,code:result.error || "model_test_invalid_response"};
      if (!result.ocr || !result.grading) throw {code:"model_test_invalid_response"};
      results.set(pipeline, {...result,pipeline}); paintResults(); status.textContent = "";
    } catch (error) { if (current()) {
      const message = arModelTestError(error, T, limits.maxImages);
      results.delete(pipeline);
      if (error.ocr || error.usage || arModelTestKnown(error.elapsed_ms)) {
        const stages = Array.isArray(error.usage?.stages) ? error.usage.stages : [];
        const metadata = key => { const stage = stages.find(x => x.stage === key); return stage ? {provider:stage.provider,model:stage.model,resolved_model:stage.resolved_model,ms:stage.ms} : {}; };
        results.set(pipeline, {...error,pipeline,failure:message,failureStage:error.stage,
          ocr:error.ocr || metadata("ocr"), grading:{...metadata("grading"),status:"error"}});
      }
      paintResults(); status.className = "arinfo bad"; status.textContent = message;
    } }
    finally { clearTimeout(timeout); controller = null; busy = false; if (current()) controls.disabled = false; }
  };
}
