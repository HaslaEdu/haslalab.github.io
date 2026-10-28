/* HaslaLab accounts, problems of the week, grading and rankings (front end).
   The account is the community account (same server, same sign-in token).  Routes:
     #/login  #/signup  #/me          sign in, sign up, my record
     #/weekly[/<week>]                this week's problems, or an earlier week's
     #/weekly/p/<id>                  one problem: type the answer or photograph it (OCR), get it graded
     #/rank[/<week|all>]              rankings
     #/weekly/admin                   admins: add problems, grade what waits; exam tokens and marking schemes
     #/lab  #/lab/<id>                exam mode (sim/exam.html): my tokens and exams, one exam's marks and pages
   Uses cmApi, cmTok, cm, esc, lang and CMT from index.html. */
"use strict";
const AT = {
  ko: {nav: "주간 문제", login: "로그인", signup: "회원가입", me: "내 기록", logout: "로그아웃",
       weekH: "이번 주 문제", weekSub: "매주 월요일 0시(한국 시각)에 새 문제가 열립니다. 주가 끝나기 전에 낸 답만 랭킹에 들어가고, 주가 끝나면 풀이가 공개됩니다.",
       closesIn: "마감까지", closed: "마감", opens: "열림", short: "단답", essay: "서술", pts: "점", level: "난이도", users: "명 도전", solvers: "명 만점",
       best: "내 최고", pending: "채점 대기", solve: "풀기", archive: "지난 주", rank: "랭킹", rankWeek: "이번 주", rankAll: "전체", rankH: "랭킹",
       rankSub: "주간 랭킹은 그 주에 낸 답의 문제별 최고 점수를 더합니다(같으면 먼저 닿은 사람이 앞). 전체 랭킹은 레이팅 순입니다.",
       ratingHelp: "레이팅 = 푼 문제 중 어려운 100문제의 난이도 점수 합 + 푼 문제 수 보너스. 단답은 정답, 서술형은 80% 이상이면 푼 문제로 칩니다. 지난 주 문제도 풀면 레이팅에 들어갑니다.",
       rating: "레이팅", nextTier: "다음 티어까지", solvedN: "푼 문제",
       nick: "닉네임", total: "점수", solved: "푼 문제", tier: "티어", empty: "아직 기록이 없습니다.", top: "이번 주 상위",
       answer: "답", answerPh: "숫자만 쓰세요 (예: 1.79)", essayPh: "풀이를 쓰세요. 수식은 $...$ 안에 LaTeX로 쓰거나 그냥 글로 써도 됩니다.",
       photo: "답안 사진 올리기", photoHint: "종이에 쓴 풀이를 찍어 올리면 글자로 읽어 줍니다(OCR). 읽은 글을 꼭 확인하고 고친 뒤 제출하세요.",
       mathMode: "수식이 많은 답안 (수식을 LaTeX로 읽기)", reading: "사진을 읽는 중…", readDone: "사진을 읽었습니다. 아래 글이 답안과 같은지 확인하고 고친 뒤 제출하세요.",
       preview: "미리보기", submit: "제출하고 채점받기", grading: "채점 중… (서술형은 30초쯤 걸립니다)", loginToSubmit: "로그인하면 제출하고 채점받을 수 있습니다.",
       result: "채점 결과", score: "점수", criteria: "채점 항목", evidence: "근거", feedback: "첨삭", good: "잘한 점", fix: "고칠 점",
       met: "충족", partial: "부분", not_met: "미충족", uncertain: "불확실", right: "정답입니다", wrong: "오답입니다",
       pendingNote: "이 서술형 답안은 AI 채점기가 아직 연결되지 않아 관리자가 채점합니다. 채점되면 여기와 랭킹에 반영됩니다.",
       errorNote: "채점 서버가 응답하지 않았습니다. 답안은 저장되었고 관리자가 다시 채점합니다.",
       evidenceIssue: "답안에 없는 내용을 근거로 든 항목은 0점으로 처리했습니다.",
       mine: "내 제출", solution: "풀이", solutionLater: "풀이는 이번 주가 끝나면 공개됩니다.", grader: "채점",
       viaOcr: "사진에서 읽음", practice: "연습(랭킹 제외)", noProblems: "이번 주 문제가 아직 없습니다.",
       oldServer: "주간 문제 서버가 아직 업데이트되지 않았습니다. 잠시 후 다시 와 주세요.", ocrOff: "사진 인식(OCR)이 아직 서버에 연결되지 않았습니다. 답을 직접 입력해 주세요.",
       myH: "내 기록", myRank: "전체 순위", myTotal: "총점", mySolved: "만점 문제", recent: "최근 제출", settings: "계정 설정(비밀번호 · 탈퇴)",
       admin: "관리", addP: "문제 추가 / 고치기", queue: "채점 대기열", save: "저장", saved: "저장했습니다", giveScore: "점수 주기", regrade: "AI로 다시 채점",
       oauthWith: {google: "Google로 계속하기", kakao: "카카오로 계속하기", naver: "네이버로 계속하기", github: "GitHub로 계속하기", discord: "Discord로 계속하기"}, oauthOr: "또는 아이디로", oauthOff: "관리자가 아직 연결하지 않았습니다",
       oauthNew: "가입했습니다. 닉네임은 계정 이름에서 가져왔으니, 원하면 아래에서 바꾸세요.", linked: "연결했습니다", linkH: "연결된 로그인", link: "연결하기", connected: "연결됨",
       nickH: "닉네임 바꾸기", change: "바꾸기", pwSet: "비밀번호 만들기 (아이디로도 로그인)", pwNew: "새 비밀번호 (8자 이상)", done: "바꿨습니다",
       tiers: {bronze: "브론즈", silver: "실버", gold: "골드", platinum: "플래티넘", diamond: "다이아몬드", ruby: "루비", master: "마스터", unrated: "Unrated"},
       err: {bad_answer: "답을 입력하세요.", bad_image: "JPEG, PNG, WebP 사진 한 장만 올릴 수 있습니다.", image_too_big: "사진이 너무 큽니다(8 MB까지).",
             ocr_off: "사진 인식(OCR)이 아직 서버에 연결되지 않았습니다.", ocr_failed: "사진을 읽지 못했습니다. 더 밝고 반듯하게 찍어 보세요.", rate_limited: "요청이 너무 많습니다. 내일 다시 시도해 주세요.",
             forbidden: "관리자만 할 수 있습니다.", bad_code: "로그인 링크가 만료되었습니다. 다시 시도해 주세요.", oauth_off: "이 로그인은 아직 연결되지 않았습니다.",
             oauth_failed: "외부 로그인에 실패했습니다. 다시 시도해 주세요.", oauth_cancelled: "로그인을 취소했습니다.", oauth_in_use: "그 계정은 이미 다른 HaslaLab 계정에 연결되어 있습니다.", bad_week: "주는 2026-W45 형식으로 쓰세요.", bad_rubric: "채점 기준(JSON)을 확인하세요.", bad_kind: "유형을 고르세요."}},
  en: {nav: "Weekly", login: "Sign in", signup: "Sign up", me: "My record", logout: "Sign out",
       weekH: "Problems of the week", weekSub: "New problems open every Monday 00:00 KST. Only answers sent while the week is open count for the rankings; the solutions are published when it closes.",
       closesIn: "Closes in", closed: "Closed", opens: "Opened", short: "Short answer", essay: "Written", pts: "pts", level: "Level", users: "tried", solvers: "full marks",
       best: "My best", pending: "Waiting", solve: "Solve", archive: "Past weeks", rank: "Rankings", rankWeek: "This week", rankAll: "All time", rankH: "Rankings",
       rankSub: "The weekly ranking adds your best score on each problem sent while the week was open (ties go to whoever got there first). All time ranks by rating.",
       ratingHelp: "Rating = the difficulty points of your 100 hardest solved problems plus a bonus for the number solved. A short answer counts when right, a written one at 80 % or more. Past weeks' problems count too.",
       rating: "Rating", nextTier: "to the next tier", solvedN: "Solved",
       nick: "Name", total: "Score", solved: "Solved", tier: "Tier", empty: "No results yet.", top: "Top this week",
       answer: "Answer", answerPh: "A number only (e.g. 1.79)", essayPh: "Write your solution. Put formulas in $...$ as LaTeX, or just write them out.",
       photo: "Upload a photo of your answer", photoHint: "Photograph your written solution and it is read into text (OCR). Check and correct the text before you submit.",
       mathMode: "Answer with many formulas (read them as LaTeX)", reading: "Reading the photo…", readDone: "The photo has been read. Check that the text below matches your answer, correct it, then submit.",
       preview: "Preview", submit: "Submit and grade", grading: "Grading… (a written answer takes about 30 s)", loginToSubmit: "Sign in to submit and be graded.",
       result: "Result", score: "Score", criteria: "Criteria", evidence: "Evidence", feedback: "Comments", good: "Good", fix: "To fix",
       met: "met", partial: "partly", not_met: "not met", uncertain: "unsure", right: "Correct", wrong: "Not correct",
       pendingNote: "No AI grader is connected yet, so an admin will grade this written answer. The score will appear here and in the rankings.",
       errorNote: "The grading server did not answer. Your answer is saved and an admin will grade it.",
       evidenceIssue: "Criteria whose evidence was not in your answer were given 0.",
       mine: "My submissions", solution: "Solution", solutionLater: "The solution is published when this week closes.", grader: "Graded by",
       viaOcr: "read from a photo", practice: "practice (not ranked)", noProblems: "No problems for this week yet.",
       oldServer: "The weekly-problem server has not been updated yet. Please come back shortly.", ocrOff: "Photo reading (OCR) is not connected yet. Please type your answer.",
       myH: "My record", myRank: "Overall rank", myTotal: "Total", mySolved: "Full marks", recent: "Recent submissions", settings: "Account settings (password, delete)",
       admin: "Admin", addP: "Add / edit a problem", queue: "Grading queue", save: "Save", saved: "Saved", giveScore: "Give score", regrade: "Regrade with AI",
       oauthWith: {google: "Continue with Google", github: "Continue with GitHub", discord: "Continue with Discord", kakao: "Continue with Kakao", naver: "Continue with NAVER"}, oauthOr: "or with a username", oauthOff: "not connected by the admin yet",
       oauthNew: "Welcome! Your nickname was taken from that account; change it below if you like.", linked: "Connected", linkH: "Sign-in methods", link: "Connect", connected: "connected",
       nickH: "Change nickname", change: "Change", pwSet: "Create a password (to sign in with your username too)", pwNew: "New password (8+ characters)", done: "Changed",
       tiers: {bronze: "Bronze", silver: "Silver", gold: "Gold", platinum: "Platinum", diamond: "Diamond", ruby: "Ruby", master: "Master", unrated: "Unrated"},
       err: {bad_answer: "Enter an answer.", bad_image: "Only one JPEG, PNG or WebP photo.", image_too_big: "The photo is too large (8 MB max).",
             ocr_off: "Photo reading (OCR) is not connected yet.", ocr_failed: "The photo could not be read. Try a brighter, straighter shot.", rate_limited: "Too many requests. Try again tomorrow.",
             forbidden: "Admins only.", bad_code: "The sign-in link has expired. Please try again.", oauth_off: "That sign-in is not connected yet.",
             oauth_failed: "The outside sign-in failed. Please try again.", oauth_cancelled: "Sign-in was cancelled.", oauth_in_use: "That account is already connected to another HaslaLab account.", bad_week: "Write the week as 2026-W45.", bad_rubric: "Check the rubric JSON.", bad_kind: "Choose a kind."}}};
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
function arDate(s) { const D = new Date(s * 1000); return (D.getMonth() + 1) + "." + D.getDate(); }
/* text with $...$ formulas: escaped, line breaks kept; KaTeX renders it afterwards */
function arText(s) { return esc(s || "").replace(/\n/g, "<br>"); }
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
async function arMount() {
  const root = document.getElementById("arRoot"); if (!root) return;
  const my = ++ar.seq, alive = () => my === ar.seq && document.getElementById("arRoot") === root;
  const parts = location.hash.replace(/^#\/?/, "").split("?")[0].split("/").filter(Boolean), [a, b, c] = parts;
  const [, h] = await Promise.all([cmLoadMe(), ar.health ? ar.health : cmHealth()]); ar.health = h;
  if (!alive()) return;
  try {
    if (a === "login" || a === "signup") return arAuth(root, a);
    if (a === "oauth") return arOauthBack(root);
    if ((ar.health.v || 0) < 4) { root.innerHTML = `<div class="cmnote">${arT().oldServer}</div>`; return; }
    if (a === "me") await arMe(root, alive);
    else if (a === "rank") await arRank(root, alive, b);
    else if (a === "weekly" && b === "p" && c) await arProblem(root, alive, +c);
    else if (a === "weekly" && b === "admin") await arAdmin(root, alive);
    else if (a === "lab") await (b ? arLabOne(root, alive, +b) : arLabList(root, alive));
    else await arWeekly(root, alive, b);
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

/* ── the week ── */
async function arWeekly(root, alive, week) {
  const T = arT(), q = week && /^\d{4}-W\d{2}$/.test(week) ? "&week=" + week : "";
  const j = await cmApi("GET", "/weekly?lang=" + lang + q); if (!alive()) return;
  let top = j.top ? {rows: j.top} : null;     // older servers leave the week's leaders out
  if (!top) { try { top = await cmApi("GET", "/rank?scope=week&week=" + j.week); } catch (e) {} if (!alive()) return; }
  const P = j.problems, open = P.length && P[0].open, ends = P.length ? P[0].closes_at : 0, starts = P.length ? P[0].opens_at : 0;
  root.innerHTML = `
    <div class="cmtop"><div><h1>${T.weekH} <span class="arwk">${esc(j.week)}</span></h1><p>${T.weekSub}</p></div>
      <div class="arwhen">${P.length ? `${arDate(starts)} – ${arDate(ends - 1)} · ${open ? `<b>${T.closesIn} ${arLeft(ends - j.now)}</b>` : T.closed}` : ""}</div></div>
    <div class="argrid"><div>
      ${P.length ? P.map((p) => `
        <a class="arcard" href="#/weekly/p/${p.id}">
          <div class="arno">${p.no}</div>
          <div class="arbody"><h3>${esc(p.title)}</h3>
            <div class="armeta"><span class="arkind ${p.kind}">${p.kind === "short" ? T.short : T.essay}</span><span>${esc(p.subject)}</span>
              ${arLevel(p.level)}<span>${p.points}${T.pts}</span>
              <span>${p.users} ${T.users} · ${p.solvers} ${T.solvers}</span></div></div>
          <div class="army">${p.best != null ? `<b>${p.best}</b><small>${T.best}</small>` : p.pending ? `<small>${T.pending}</small>` : `<span class="cmbtn sm pri">${T.solve}</span>`}</div>
        </a>`).join("") : `<div class="cmnote">${T.noProblems}</div>`}
      ${j.weeks && j.weeks.length > 1 ? `<h3 class="arh3">${T.archive}</h3><div class="arweeks">${j.weeks.map((w) => `<a href="#/weekly/${w.week}" class="${w.week === j.week ? "on" : ""}">${esc(w.week)}<small>${arDate(w.o)}–${arDate(w.c - 1)}</small></a>`).join("")}</div>` : ""}
    </div><aside class="arside">
      <div class="arpanel"><h3>${T.top}</h3>${top && top.rows.length ? `<ol class="artop">${top.rows.slice(0, 8).map((r) => `<li><span class="arwho">${cmAv(r.nickname, "s", r.av)}<i>${esc(r.nickname)}</i></span>${tierIcon(r.lv, 14)}<b>${r.total}</b></li>`).join("")}</ol>` : `<p class="arempty">${T.empty}</p>`}
        <a class="cmbtn sm" href="#/rank/week">${T.rank} →</a></div>
      ${cm.me && cm.me.role === "admin" ? `<a class="cmbtn sm" href="#/weekly/admin">⚙ ${T.admin}</a>` : ""}
    </aside></div>`;
}

/* ── one problem ── */
function arResult(s, prob) {
  const T = arT(), d = s.detail || {};
  if (s.status === "pending") return `<div class="cmnote">${T.pendingNote}</div>`;
  if (s.status === "error") return `<div class="cmnote">${T.errorNote}</div>`;
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
async function arProblem(root, alive, id) {
  const T = arT(), j = await cmApi("GET", `/problems/${id}?lang=${lang}`); if (!alive()) return;
  const p = j.problem, now = Math.floor(Date.now() / 1000), ocrOn = j.health && j.health.ocr;
  root.innerHTML = `
    <div class="arcrumb"><a href="#/weekly/${esc(p.week)}">← ${T.weekH} ${esc(p.week)}</a></div>
    <div class="arprob">
      <div class="arph"><span class="arno">${p.no}</span><div><h1>${esc(p.title)}</h1>
        <div class="armeta"><span class="arkind ${p.kind}">${p.kind === "short" ? T.short : T.essay}</span><span>${esc(p.subject)}</span>${arLevel(p.level)}<span>${esc(tierName(p.level))}</span>
          <span>${p.points}${T.pts}</span><span>${p.open ? `${T.closesIn} ${arLeft(p.closes_at - now)}` : T.closed}</span>${p.source ? `<span>${esc(p.source)}</span>` : ""}</div></div></div>
      <div class="arstmt" id="arStmt">${arText(p.body)}</div>
      ${p.criteria ? `<div class="arcrit">${p.criteria.map((c) => `<span><b>${esc(c.id)}</b> ${esc(c.name)} · ${c.max}${T.pts}</span>`).join("")}</div>` : ""}
    </div>
    <div class="arpanel" id="arAns">
      <h3>${T.answer}</h3>
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
          <button class="cmbtn pri" type="submit">${T.submit}</button></form>`}
      <div id="arOut"></div>
    </div>
    ${p.mine && p.mine.length ? `<div class="arpanel"><h3>${T.mine}</h3>${p.mine.map((s) => `
      <details class="arsub"><summary><b>${s.status === "graded" ? s.score + " / " + p.points : T[s.status] || s.status}</b>
        <span>${cmFull(s.created_at)}</span>${s.via_ocr ? `<small>${T.viaOcr}</small>` : ""}${s.in_week ? "" : `<small>${T.practice}</small>`}</summary>
        <pre class="aranswer">${esc(s.answer)}</pre>${arResult(s, p)}</details>`).join("")}</div>` : ""}
    <div class="arpanel"><h3>${T.solution}</h3>${p.solution ? `<div class="arstmt" id="arSol">${arText(p.solution)}</div>` : `<p class="arempty">${T.solutionLater}</p>`}</div>`;
  arMath(root);
  const lg = root.querySelector("#arLogin"); if (lg) lg.onclick = () => { try { sessionStorage.setItem("hlCmBack", location.hash); } catch (e) {} };
  const f = root.querySelector("#arF"); if (!f) return;
  const out = root.querySelector("#arOut"); let viaOcr = false;
  const ta = f.querySelector("textarea");
  if (ta) {
    const key = "hlArDraft" + id; try { ta.value = localStorage.getItem(key) || ""; } catch (e) {}
    const prev = root.querySelector("#arPrev"); let tm = 0;
    const upd = () => { prev.innerHTML = arText(ta.value); arMath(prev); try { localStorage.setItem(key, ta.value); } catch (e) {} };
    ta.oninput = () => { clearTimeout(tm); tm = setTimeout(upd, 350); }; upd();
    const fi = f.querySelector("input[type=file]"), info = f.querySelector(".arinfo"), shot = f.querySelector(".arshot");
    fi.onchange = async () => {
      const file = fi.files[0]; if (!file) return;
      shot.hidden = false; shot.querySelector("img").src = URL.createObjectURL(file);
      info.hidden = false; info.textContent = T.reading;
      const fd = new FormData(); fd.append("image", file);
      try {
        const r = await fetch(cmBase() + "/api/ocr?mode=" + (f.math.checked ? "math" : "text"), {method: "POST", headers: {Authorization: "Bearer " + cmTok()}, body: fd});
        const k = await r.json().catch(() => ({error: "server_error"}));
        if (!r.ok) throw {code: k.error};
        ta.value = (ta.value.trim() ? ta.value.trim() + "\n\n" : "") + k.text; viaOcr = true; upd();
        info.textContent = T.readDone; info.className = "arinfo ok"; ta.focus();
      } catch (e) { info.textContent = arErr(e); info.className = "arinfo bad"; }
      fi.value = "";
    };
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
async function arRank(root, alive, which) {
  const T = arT(), week = which && /^\d{4}-W\d{2}$/.test(which) ? which : null, scope = which === "all" ? "all" : "week";
  const j = await cmApi("GET", "/rank?scope=" + scope + (week ? "&week=" + week : "")); if (!alive()) return;
  root.innerHTML = `
    <div class="cmtop"><div><h1>${T.rankH}${j.week ? ` <span class="arwk">${esc(j.week)}</span>` : ""}</h1><p>${T.rankSub}</p></div>
      <div class="cmseg"><a href="#/rank/week" class="${scope === "week" ? "on" : ""}">${T.rankWeek}</a><a href="#/rank/all" class="${scope === "all" ? "on" : ""}">${T.rankAll}</a></div></div>
    <div class="arpanel">${j.rows.length ? `<table class="cmtbl artbl"><thead><tr><th style="width:56px">#</th><th>${T.nick}</th><th style="width:150px">${T.tier}</th>
      <th style="width:90px">${scope === "all" ? T.rating : T.total}</th><th style="width:80px">${T.solved}</th></tr></thead>
      <tbody>${j.rows.map((r) => `<tr class="${cm.me && r.nickname === cm.me.nickname ? "armine" : ""}"><td><b>${r.rank}</b></td><td class="t">${cmAv(r.nickname, "s", r.av)} ${esc(r.nickname)}</td>
        <td>${arTier(r.lv)}</td><td><b style="color:${TIER_COL[tierKey(r.lv)]}">${scope === "all" ? (r.rating ?? r.total) : r.total}</b></td><td>${r.solved}</td></tr>`).join("")}</tbody></table>`
      : `<p class="arempty">${T.empty}</p>`}</div>
    <p class="arfoot">${T.ratingHelp}</p>`;
}

/* ── my record ── */
async function arMe(root, alive) {
  const T = arT();
  if (!cm.me) { try { sessionStorage.setItem("hlCmBack", "#/me"); } catch (e) {} location.hash = "#/login"; return; }
  const j = await cmApi("GET", "/me/stats"); if (!alive()) return;
  j.lv = j.lv || 0; j.rating = j.rating || 0;               // a server from before the rating sends neither
  root.innerHTML = `
    <div class="cmtop"><div><h1>${cmAv(cm.me.nickname, "", cm.me.avatar)} ${esc(cm.me.nickname)} ${arTier(j.lv)}</h1><p>@${esc(cm.me.username)}</p></div>
      <div style="display:flex;gap:6px"><a class="cmbtn sm" href="#/community/account">${T.settings}</a><button class="cmbtn sm" id="arLogout">${T.logout}</button></div></div>
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
    <div class="arpanel"><h3>${T.recent}</h3>${j.subs.length ? `<table class="cmtbl artbl"><tbody>${j.subs.map((s) => `<tr><td style="width:96px">${esc(s.week)}</td>
      <td class="t"><a href="#/weekly/p/${s.problem_id}">${s.no}. ${esc(lang === "en" ? s.title_en : s.title_ko)}</a></td>
      <td style="width:110px"><b>${s.status === "graded" ? s.score + " / " + s.points : T[s.status] || s.status}</b></td><td style="width:130px">${cmShort(s.created_at)}</td></tr>`).join("")}</tbody></table>` : `<p class="arempty">${T.empty}</p>`}</div>`;
  cmAvatarForm(root.querySelector("#arAv"), () => { const h = root.querySelector(".cmtop h1"); if (h) h.innerHTML = `${cmAv(cm.me.nickname, "", cm.me.avatar)} ${esc(cm.me.nickname)} ${arTier(j.lv)}`; });
  const nf = root.querySelector("#arNick");
  const nickFree = cmNickCheck(nf.n, nf.querySelector(".cmnick"), cm.me.nickname);
  nf.onsubmit = async (e) => { e.preventDefault(); const info = nf.querySelector(".arinfo"); info.textContent = "";
    if (await nickFree() === false) { info.textContent = cmErr({code: "nickname_taken"}); return; }
    try { const r = await cmApi("PATCH", "/me", {nickname: nf.n.value.trim()}); cm.me.nickname = r.nickname; nf.n.value = r.nickname; info.textContent = T.done; arChip();
      const h = root.querySelector(".cmtop h1"); if (h) h.innerHTML = `${cmAv(cm.me.nickname, "", cm.me.avatar)} ${esc(cm.me.nickname)} ${arTier(j.lv)}`; } catch (er) { info.textContent = arErr(er); } };
  try {
    const idj = await cmApi("GET", "/me/identities"), have = idj.identities.map((x) => x.provider), box = root.querySelector("#arIds");
    box.innerHTML = `<div class="oauth">${[...new Set(arProvs().concat(have))].map((p) => have.includes(p) ? `<span class="${p}">${OAUTH_ICON[p]}${(T.oauthWith[p] || p).replace(/로 계속하기|Continue with /g, "")} · ${T.connected}</span>`
      : idj.providers.includes(p) && arProvs().includes(p) ? `<a href="#" data-p="${p}" class="${p}">${OAUTH_ICON[p]}${(T.oauthWith[p] || p).replace(/로 계속하기|Continue with /g, "")} · ${T.link}</a>` : "").join("")}</div>
      ${idj.has_pw ? "" : `<form id="arPw" class="arq"><span>${T.pwSet}</span><input type="password" name="pw" placeholder="${T.pwNew}" minlength="8"><button class="cmbtn sm">${T.save}</button><span class="arinfo"></span></form>`}`;
    for (const a of box.querySelectorAll("a[data-p]")) a.onclick = async (e) => { e.preventDefault(); try { const t = await cmApi("POST", "/oauth/ticket"); sessionStorage.setItem("hlCmBack", "#/me"); arOauthStart(a.dataset.p, t.ticket); } catch (er) { cmToast(arErr(er)); } };
    const pf = box.querySelector("#arPw"); if (pf) pf.onsubmit = async (e) => { e.preventDefault(); try { await cmApi("POST", "/me/password", {password: pf.pw.value}); pf.querySelector(".arinfo").textContent = T.done; } catch (er) { pf.querySelector(".arinfo").textContent = arErr(er); } };
  } catch (e) {}
  if ((ar.health || {}).lab) cmApi("GET", "/lab/active").then((x) => { const el = root.querySelector("#arLabMe"); if (!el) return; const L = LBT[lang === "en" ? "en" : "ko"];
    el.innerHTML = `<h3>⏱ ${L.h}</h3><p style="margin:0 0 8px">${L.tokens(x.tokens)}${x.active ? ` · <b>${L.st[x.active.status]}</b>: ${esc(x.active.comp.toUpperCase())} ${x.active.year}` : ""}</p><a class="cmbtn sm" href="#/lab">${L.all}</a>`; }, () => {});
  else { const el = root.querySelector("#arLabMe"); if (el) el.remove(); }
  root.querySelector("#arLogout").onclick = async () => { try { await cmApi("POST", "/logout"); } catch (e) {} cmTok(null); cm.me = null; location.hash = "#/weekly"; arChip(); };
}

/* ── exam mode: tokens, exams, marks ── */
const LBT = {
  ko: {h: "실전 모드", sub: "대회처럼 5시간 실험 + 30분 답안 스캔. 시작할 때마다 실전 토큰 1개를 씁니다. 진행 중인 시험으로 돌아갈 때는 쓰지 않습니다.",
       tokens: (n) => `남은 실전 토큰 <b>${n}</b>개`, ledger: "토큰 기록", all: "실전 모드 기록", mine: "내 시험", none: "아직 친 시험이 없습니다.",
       start: "시작", grant: "받음", revoke: "회수", refund: "돌려받음", resume: "이어하기", active: "진행 중인 시험", total: "총점", pages: "보낸 쪽",
       st: {running: "실험 중", scanning: "스캔 중", grading: "채점 중", graded: "채점 완료", pending: "채점 대기", error: "채점 오류", empty: "제출 없음"},
       why: {no_scheme: "이 실험의 채점 기준이 아직 등록되지 않아 관리자가 채점합니다.", no_grader: "AI 채점기가 연결되지 않아 관리자가 채점합니다.", no_solution: "이 실험은 공식 솔루션 파일이 없어 채점 기준표를 만들 수 없습니다."},
       err: "채점 서버가 응답하지 않았습니다. 관리자가 다시 채점합니다.", empty: "이 실험에서 보낸 쪽이 없습니다.", sol: "풀이 · 채점 기준", answer: "답안지", working: "Working sheet",
       del: "이 기록 지우기", delQ: "이 시험 기록과 사진을 지울까요? 토큰은 돌아오지 않습니다.", howGet: "토큰은 관리자가 나누어 줍니다. 더 필요하면 커뮤니티에 문의하세요.",
       admin: "실전 모드 관리", grantH: "토큰 주기 / 회수", user: "아이디 또는 닉네임", delta: "개수 (+2, -1)", look: "조회", rubH: "채점 기준 (실험별)", load: "불러오기",
       queue: "채점 대기 시험", give: "점수 주기", regrade: "AI로 다시 채점", points: "만점",
       reportH: "성적표", examNo: "수험번호", cand: "응시자", exam: "시험", date: "응시일", pct: "백분율", rank: "순위", rankV: (k, n) => `${n}명 중 ${k}위`, top: "상위", avg: "응시자 평균", max: "최고",
       retryNote: "다시 응시한 시험입니다. 순위는 다른 응시자들의 첫 응시와 비교한 것입니다.", examList: "시험 목록",
       item: "채점 항목", evid: "근거", rulesH: "적용 규정", by: {code: "범위·검증", model: "AI 판단"}, sheetA: "답안지", sheetW: "연습지", page: "쪽",
       regH: "채점 규정", regNote: "엄격 채점: 읽을 수 없는 것은 응시자 책임이며 다시 읽어 주지 않습니다.", noSol: "이 실험은 공식 솔루션 파일이 없어 채점 기준표를 만들 수 없습니다."},
  en: {h: "Exam mode", sub: "Five hours of experiments as on the day, then 30 minutes to scan your answers. Each start uses one exam token; going back to an exam in progress does not.",
       tokens: (n) => `Exam tokens left: <b>${n}</b>`, ledger: "Token history", all: "Exam mode record", mine: "My exams", none: "No exams yet.",
       start: "start", grant: "received", revoke: "taken back", refund: "refunded", resume: "Resume", active: "In progress", total: "Total", pages: "Pages sent",
       st: {running: "experiments running", scanning: "scanning", grading: "grading", graded: "graded", pending: "waiting for a grader", error: "grading error", empty: "nothing sent"},
       why: {no_scheme: "This experiment's marking scheme is not entered yet, so an admin will grade it.", no_grader: "No AI grader is connected, so an admin will grade it.", no_solution: "This experiment has no official solution file, so no marking scheme could be drawn."},
       err: "The grading server did not answer. An admin will grade it again.", empty: "No pages were sent for this experiment.", sol: "Solution & marking scheme", answer: "Answer sheet", working: "Working sheet",
       del: "Delete this record", delQ: "Delete this exam and its photos? The token is not given back.", howGet: "Tokens are handed out by the admins. Ask in the community if you need more.",
       admin: "Exam mode admin", grantH: "Give / take tokens", user: "username or nickname", delta: "how many (+2, -1)", look: "Look up", rubH: "Marking schemes (per experiment)", load: "Load",
       queue: "Exams waiting for a grader", give: "Give score", regrade: "Regrade with AI", points: "full marks",
       reportH: "Score report", examNo: "Candidate no.", cand: "Candidate", exam: "Exam", date: "Date", pct: "Percentage", rank: "Rank", rankV: (k, n) => `${k} of ${n}`, top: "top", avg: "Average", max: "Best",
       retryNote: "This was a second sitting; the rank compares it with the other candidates' first sittings.", examList: "Exam list",
       item: "Item", evid: "Evidence", rulesH: "Rules", by: {code: "interval / check", model: "AI judgement"}, sheetA: "answer sheet", sheetW: "working sheet", page: "p.",
       regH: "Grading regulation", regNote: "Strict marking: whatever cannot be read is the candidate's responsibility and is not re-read.", noSol: "This experiment has no official solution file, so no marking scheme could be drawn."}};
const lbt = () => LBT[lang === "en" ? "en" : "ko"];
/* the catalogue's solution sheet for an exam's experiment, when the site has one */
function arLabSol(s, task) {
  const c = DATA[s.comp], y = c && c.years.find((x) => x.y === s.year), p = y && y.problems.find((x) => x.id === task || (typeof examTask === "function" && examTask(x) === task)), v = p && p.files && p.files.sol;
  return typeof v === "string" ? v : v ? (v[lang] || v.ko || v.en) : "";
}
async function arLabList(root, alive) {
  const L = lbt();
  if (!cm.me) { try { sessionStorage.setItem("hlCmBack", "#/lab"); } catch (e) {} location.hash = "#/login"; return; }
  const [a, tk, ls] = await Promise.all([cmApi("GET", "/lab/active"), cmApi("GET", "/lab/tokens"), cmApi("GET", "/lab/sessions")]); if (!alive()) return;
  const act = a.active;
  root.innerHTML = `
    <div class="cmtop"><div><h1>⏱ ${L.h}</h1><p>${L.sub}</p></div></div>
    <div class="arstats"><div><small>${lang === "en" ? "Tokens" : "실전 토큰"}</small><b>${tk.tokens}</b></div><div><small>${L.mine}</small><b>${ls.sessions.length}</b></div></div>
    ${act ? `<div class="arpanel"><h3>${L.active}</h3><p style="margin:0 0 8px"><b>${esc(act.comp.toUpperCase())} ${act.year}</b> · ${L.st[act.status]}</p>
      ${act.entry ? `<a class="cmbtn pri" href="sim/exam.html${esc(act.entry)}&lang=${lang}">${L.resume}</a>` : ""}</div>` : ""}
    <div class="arpanel"><h3>${L.mine}</h3>${ls.sessions.length ? `<table class="cmtbl artbl"><tbody>${ls.sessions.map((x) => `<tr>
      <td class="t"><a href="#/lab/${x.id}"><b>${esc(x.comp.toUpperCase())} ${x.year}</b> ${esc(x.tasks.join(" + "))}</a></td>
      <td style="width:150px">${L.st[x.status] || esc(x.status)}</td><td style="width:110px"><b>${x.status === "graded" ? x.score + (x.points ? " / " + x.points : "") : "–"}</b></td>
      <td style="width:130px">${cmShort(x.created_at)}</td></tr>`).join("")}</tbody></table>` : `<p class="arempty">${L.none}</p>`}</div>
    <div class="arpanel"><h3>${L.ledger}</h3><p class="arempty" style="margin-top:0">${L.howGet}</p>${tk.ledger.length ? `<table class="cmtbl artbl"><tbody>${tk.ledger.map((x) => `<tr>
      <td style="width:80px"><b style="color:${x.delta < 0 ? "#c0392b" : "#1e8449"}">${x.delta > 0 ? "+" : ""}${x.delta}</b></td><td class="t">${L[x.reason] || esc(x.reason)}${x.exam_key ? " · " + esc(x.exam_key.toUpperCase()) : ""}${x.note ? " · " + esc(x.note) : ""}</td>
      <td style="width:130px">${cmShort(x.created_at)}</td></tr>`).join("")}</tbody></table>` : ""}</div>`;
}
/* one experiment graded from the images: per item the mark, how it was decided, where its evidence is and the rules that cost marks */
function arLabItems(x, reg) {
  const L = lbt(), T = arT(), rule = (id) => { const r = reg && reg.rules.find((y) => y.id === id); return `<span class="arrule" title="${esc(r ? (lang === "en" ? r.en : r.ko) : id)}">${esc(id)}</span>`; };
  return `<div class="arres ${x.score >= x.points ? "ok" : ""}"><b>${T.score}</b><span>${x.score} / ${x.points}${T.pts}</span>${x.grader ? `<small>${T.grader}: ${esc(x.grader)}${x.regulation ? " · " + esc(x.regulation) : ""}</small>` : ""}</div>
    <table class="cmtbl artbl"><thead><tr><th style="width:40%">${L.item}</th><th style="width:96px">${T.score}</th><th>${L.evid}</th><th style="width:90px">${L.rulesH}</th></tr></thead><tbody>
    ${x.items.map((i) => `<tr><td class="t"><b>${esc(i.id)}</b> ${esc(i.what || "")}${i.note ? `<div class="arnote">${esc(i.note)}</div>` : ""}</td>
      <td><b>${i.got}</b>/${i.points}<div class="ardec ${i.decision}">${T[i.decision] || ""}</div><div class="arby">${L.by[i.by] || ""}</div></td>
      <td class="t">${i.page ? `${L.page === "p." ? "p." + i.page : i.page + L.page} · ${i.sheet === "answer" ? L.sheetA : L.sheetW}` : "—"}${i.value != null ? ` · <q>${esc(i.value)}</q>` : ""}</td>
      <td>${(i.rules || []).map(rule).join(" ")}</td></tr>`).join("")}</tbody></table>
    ${(x.feedback || []).length ? `<h4 class="arh4">${T.feedback}</h4><ul class="arfb">${x.feedback.map((f) => `<li class="${f.kind}"><em>${f.kind === "good" ? T.good : T.fix}</em>${f.label ? `<q>${esc(f.label)}</q> ` : ""}${esc(f.note)}</li>`).join("")}</ul>` : ""}`;
}
async function arLabOne(root, alive, id) {
  const L = lbt(), T = arT();
  if (!cm.me) { try { sessionStorage.setItem("hlCmBack", "#/lab/" + id); } catch (e) {} location.hash = "#/login"; return; }
  const s = (await cmApi("GET", `/lab/sessions/${id}`)).session; if (!alive()) return;
  const per = (s.detail && s.detail.tasks) || {}, open = s.status === "running" || s.status === "scanning";
  /* the experiment alone, against the year's real contestants (sim/labmedal.js) */
  const medal = s.status === "graded" && window.labMedal ? window.labMedal.estimate(await window.labMedal.load("sim/labmedals.json"), s.comp, s.year, s.score, s.points, s.tasks) : null;
  if (!alive()) return;
  root.innerHTML = `
    <div class="cmtop"><div><h1>⏱ ${esc(s.comp.toUpperCase())} ${s.year} · ${esc(s.tasks.join(" + "))}</h1><p>${cmFull(s.started_at).slice(0, 16)} · ${L.st[s.status] || esc(s.status)}</p></div>
      <div style="display:flex;gap:6px"><a class="cmbtn sm" href="#/${esc(s.comp)}/exam">${L.examList}</a><a class="cmbtn sm" href="#/lab">${L.all}</a>${open && s.entry ? `<a class="cmbtn sm pri" href="sim/exam.html${esc(s.entry)}&lang=${lang}">${L.resume}</a>` : ""}</div></div>
    <div class="arpanel arrep"><h3>📄 ${L.reportH}</h3><table class="cmtbl artbl"><tbody>
      <tr><th>${L.examNo}</th><td><b>HL-${esc((s.comp + s.year).toUpperCase())}-${String(s.id).padStart(6, "0")}</b></td><th>${L.cand}</th><td>${esc(s.nickname || cm.me.nickname)}</td></tr>
      <tr><th>${L.exam}</th><td>${esc(s.comp.toUpperCase())} ${s.year} · ${esc(s.tasks.join(" + "))}</td><th>${L.date}</th><td>${cmFull(s.started_at).slice(0, 16)}</td></tr></tbody></table>
      ${s.status === "graded" ? `<div class="arstats" style="margin:14px 0 0"><div><small>${L.total}</small><b>${s.score} / ${s.points ?? "?"}</b></div>
        ${s.standing ? `<div><small>${L.pct}</small><b>${s.standing.mine}%</b></div><div><small>${L.rank}</small><b>${L.rankV(s.standing.rank, s.standing.n)}</b></div>
        <div><small>${L.top}</small><b>${s.standing.top_pct}%</b></div><div><small>${L.avg} · ${L.max}</small><b>${s.standing.avg}% · ${s.standing.max}%</b></div>` : ""}</div>
        ${s.standing && !s.standing.first ? `<p class="arempty" style="margin:8px 0 0">${L.retryNote}</p>` : ""}${medal ? window.labMedal.html(medal, lang) : ""}` : ""}</div>
    ${s.tasks.map((t) => { const x = per[t] || {}, sol = arLabSol(s, t);
      const body = x.status === "graded" && Array.isArray(x.items) ? arLabItems(x, s.regulation)
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
  root.querySelectorAll("details.arsub").forEach((d) => d.addEventListener("toggle", async () => {
    const box = d.querySelector("[data-img]"); if (!d.open || !box || box.firstChild) return;
    try { const r = await fetch(cmBase() + `/api/lab/pages/${box.dataset.img}/img`, {headers: {Authorization: "Bearer " + cmTok()}}); if (r.ok) box.innerHTML = `<img alt="" style="width:100%;border-radius:8px" src="${URL.createObjectURL(await r.blob())}">`; } catch (e) {}
  }));
  const del = root.querySelector("#arLabDel");
  if (del) del.onclick = async () => { if (!confirm(L.delQ)) return; try { await cmApi("DELETE", `/lab/sessions/${id}`); location.hash = "#/lab"; } catch (e) { cmToast(arErr(e)); } };
}
async function arLabAdmin(box) {
  const L = lbt();
  let q; try { q = await cmApi("GET", "/admin/lab/queue"); } catch (e) { box.remove(); return; }
  box.innerHTML = `<h3>⏱ ${L.admin}</h3>
    <h4 class="arh4">${L.grantH}</h4>
    <form class="arq" id="lbTok"><input name="u" placeholder="${L.user}"><input name="d" type="number" placeholder="${L.delta}" style="width:120px"><input name="n" placeholder="note">
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
    <div class="cmtop"><div><h1>${T.admin}</h1></div></div>
    <div class="arpanel"><h3>${T.queue} (${qj.subs.length})</h3>${qj.subs.map((s) => `
      <details class="arsub"><summary><b>#${s.id}</b> ${esc(s.title_ko)} · ${esc(s.nickname)} · ${esc(s.status)}</summary><pre class="aranswer">${esc(s.answer)}</pre>
        <pre class="aranswer small">${esc(s.rubric || "")}</pre>
        <form class="arq" data-id="${s.id}"><input name="score" type="number" min="0" max="${s.points}" placeholder="0–${s.points}"><input name="note" placeholder="note">
          <button class="cmbtn sm pri" type="submit">${T.giveScore}</button><button class="cmbtn sm" type="button" data-re="1">${T.regrade}</button></form></details>`).join("") || `<p class="arempty">${T.empty}</p>`}</div>
    <div class="arpanel"><h3>${T.addP}</h3>
      <select id="arPick" class="cmsel"><option value="">— new —</option>${pj.problems.map((x) => `<option value="${x.id}">${esc(x.week)} #${x.no} ${esc(x.title_ko)}</option>`).join("")}</select>
      <form id="arPF" class="arpf">${F.map((k) => big.includes(k) ? `<label>${k}<textarea name="${k}" rows="4"></textarea></label>` : `<label>${k}<input name="${k}"></label>`).join("")}
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
