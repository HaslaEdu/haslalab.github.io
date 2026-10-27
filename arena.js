/* HaslaLab accounts, problems of the week, grading and rankings (front end).
   The account is the community account (same server, same sign-in token).  Routes:
     #/login  #/signup  #/me          sign in, sign up, my record
     #/weekly[/<week>]                this week's problems, or an earlier week's
     #/weekly/p/<id>                  one problem: type the answer or photograph it (OCR), get it graded
     #/rank[/<week|all>]              rankings
     #/weekly/admin                   admins: add problems, grade what waits
   Uses cmApi, cmTok, cm, esc, lang and CMT from index.html. */
"use strict";
const AT = {
  ko: {nav: "주간 문제", login: "로그인", signup: "회원가입", me: "내 기록", logout: "로그아웃",
       weekH: "이번 주 문제", weekSub: "매주 월요일 0시(한국 시각)에 새 문제가 열립니다. 주가 끝나기 전에 낸 답만 랭킹에 들어가고, 주가 끝나면 풀이가 공개됩니다.",
       closesIn: "마감까지", closed: "마감", opens: "열림", short: "단답", essay: "서술", pts: "점", level: "난이도", users: "명 도전", solvers: "명 만점",
       best: "내 최고", pending: "채점 대기", solve: "풀기", archive: "지난 주", rank: "랭킹", rankWeek: "이번 주", rankAll: "전체", rankH: "랭킹",
       rankSub: "문제마다 가장 높은 점수를 더합니다. 같은 점수라면 그 점수에 먼저 닿은 사람이 앞섭니다. 주가 열려 있는 동안 낸 답만 셉니다.",
       nick: "닉네임", total: "점수", solved: "만점", tier: "티어", empty: "아직 기록이 없습니다.", top: "이번 주 상위",
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
       tiers: {bronze: "브론즈", silver: "실버", gold: "골드", platinum: "플래티넘", diamond: "다이아몬드", ruby: "루비"},
       err: {bad_answer: "답을 입력하세요.", bad_image: "JPEG, PNG, WebP 사진 한 장만 올릴 수 있습니다.", image_too_big: "사진이 너무 큽니다(8 MB까지).",
             ocr_off: "사진 인식(OCR)이 아직 서버에 연결되지 않았습니다.", ocr_failed: "사진을 읽지 못했습니다. 더 밝고 반듯하게 찍어 보세요.", rate_limited: "요청이 너무 많습니다. 내일 다시 시도해 주세요.",
             forbidden: "관리자만 할 수 있습니다.", bad_week: "주는 2026-W45 형식으로 쓰세요.", bad_rubric: "채점 기준(JSON)을 확인하세요.", bad_kind: "유형을 고르세요."}},
  en: {nav: "Weekly", login: "Sign in", signup: "Sign up", me: "My record", logout: "Sign out",
       weekH: "Problems of the week", weekSub: "New problems open every Monday 00:00 KST. Only answers sent while the week is open count for the rankings; the solutions are published when it closes.",
       closesIn: "Closes in", closed: "Closed", opens: "Opened", short: "Short answer", essay: "Written", pts: "pts", level: "Level", users: "tried", solvers: "full marks",
       best: "My best", pending: "Waiting", solve: "Solve", archive: "Past weeks", rank: "Rankings", rankWeek: "This week", rankAll: "All time", rankH: "Rankings",
       rankSub: "Your best score on each problem is added up. On equal scores, whoever reached it first is ahead. Only answers sent while a week is open count.",
       nick: "Name", total: "Score", solved: "Full", tier: "Tier", empty: "No results yet.", top: "Top this week",
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
       tiers: {bronze: "Bronze", silver: "Silver", gold: "Gold", platinum: "Platinum", diamond: "Diamond", ruby: "Ruby"},
       err: {bad_answer: "Enter an answer.", bad_image: "Only one JPEG, PNG or WebP photo.", image_too_big: "The photo is too large (8 MB max).",
             ocr_off: "Photo reading (OCR) is not connected yet.", ocr_failed: "The photo could not be read. Try a brighter, straighter shot.", rate_limited: "Too many requests. Try again tomorrow.",
             forbidden: "Admins only.", bad_week: "Write the week as 2026-W45.", bad_rubric: "Check the rubric JSON.", bad_kind: "Choose a kind."}}};
const TIER_COL = {bronze: "#ad5600", silver: "#435f7a", gold: "#ec9a00", platinum: "#27e2a4", diamond: "#00b4fc", ruby: "#ff0062"};
const ar = {seq: 0, health: null};
const arT = () => AT[lang];
const arErr = (e) => (arT().err[e && e.code]) || cmErr(e);
function arTier(t) { return `<span class="artier" style="--c:${TIER_COL[t] || "#888"}">${esc(arT().tiers[t] || t)}</span>`; }
function arLeft(sec) { if (sec <= 0) return arT().closed; const d = Math.floor(sec / 86400), h = Math.floor(sec % 86400 / 3600), m = Math.floor(sec % 3600 / 60);
  return lang === "ko" ? (d ? d + "일 " : "") + h + "시간 " + m + "분" : (d ? d + "d " : "") + h + "h " + m + "m"; }
function arDate(s) { const D = new Date(s * 1000); return (D.getMonth() + 1) + "." + D.getDate(); }
function arStars(n) { return "★".repeat(n) + "<span style=\"opacity:.25\">" + "★".repeat(Math.max(0, 5 - n)) + "</span>"; }
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
  if (!cm.meChecked && cmTok()) { try { cm.me = (await cmApi("GET", "/me")).user; } catch (e) {} cm.meChecked = true; }
  const T = arT();
  box.innerHTML = cm.me
    ? `<a href="#/me" class="acct-me" title="${esc(T.me)}">${cmAv(cm.me.nickname, "s")}<span>${esc(cm.me.nickname)}</span></a>`
    : `<a href="#/login" class="acct-in" data-ar="login">${T.login}</a>`;
  const a = box.querySelector("[data-ar=login]"); if (a) a.onclick = () => { try { sessionStorage.setItem("hlCmBack", location.hash); } catch (e) {} };
}

function viewArena(first) { return `<div class="shell cm ar"><div id="arRoot" data-r="${esc(first)}"><div class="cmnote">…</div></div></div>`; }
async function arMount() {
  const root = document.getElementById("arRoot"); if (!root) return;
  const my = ++ar.seq, alive = () => my === ar.seq && document.getElementById("arRoot") === root;
  const parts = location.hash.replace(/^#\/?/, "").split("?")[0].split("/").filter(Boolean), [a, b, c] = parts;
  if (!cm.meChecked && cmTok()) { try { cm.me = (await cmApi("GET", "/me")).user; } catch (e) {} cm.meChecked = true; }
  if (!ar.health) { try { const h = await cmApi("GET", "/health"); ar.health = h; } catch (e) { ar.health = {v: 0}; } }
  if (!alive()) return;
  try {
    if (a === "login" || a === "signup") return arAuth(root, a);
    if ((ar.health.v || 0) < 4) { root.innerHTML = `<div class="cmnote">${arT().oldServer}</div>`; return; }
    if (a === "me") await arMe(root, alive);
    else if (a === "rank") await arRank(root, alive, b);
    else if (a === "weekly" && b === "p" && c) await arProblem(root, alive, +c);
    else if (a === "weekly" && b === "admin") await arAdmin(root, alive);
    else await arWeekly(root, alive, b);
  } catch (e) { if (alive()) root.innerHTML = `<div class="cmnote">${esc(arErr(e))}</div>`; }
}

/* ── sign in / up: the community forms, on the site's own pages ── */
function arAuth(root, which) {
  if (cm.me) { cmBack(); return; }
  (which === "login" ? cmLogin : cmSignup)(root);
  for (const l of root.querySelectorAll("a[href='#/community/signup'],a[href='#/community/login']")) l.setAttribute("href", l.getAttribute("href").replace("/community", ""));
}

/* ── the week ── */
async function arWeekly(root, alive, week) {
  const T = arT(), q = week && /^\d{4}-W\d{2}$/.test(week) ? "&week=" + week : "";
  const j = await cmApi("GET", "/weekly?lang=" + lang + q); if (!alive()) return;
  let top = null; try { top = await cmApi("GET", "/rank?scope=week&week=" + j.week); } catch (e) {}
  if (!alive()) return;
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
              <span class="arlv" title="${T.level}">${arStars(p.level)}</span><span>${p.points}${T.pts}</span>
              <span>${p.users} ${T.users} · ${p.solvers} ${T.solvers}</span></div></div>
          <div class="army">${p.best != null ? `<b>${p.best}</b><small>${T.best}</small>` : p.pending ? `<small>${T.pending}</small>` : `<span class="cmbtn sm pri">${T.solve}</span>`}</div>
        </a>`).join("") : `<div class="cmnote">${T.noProblems}</div>`}
      ${j.weeks && j.weeks.length > 1 ? `<h3 class="arh3">${T.archive}</h3><div class="arweeks">${j.weeks.map((w) => `<a href="#/weekly/${w.week}" class="${w.week === j.week ? "on" : ""}">${esc(w.week)}<small>${arDate(w.o)}–${arDate(w.c - 1)}</small></a>`).join("")}</div>` : ""}
    </div><aside class="arside">
      <div class="arpanel"><h3>${T.top}</h3>${top && top.rows.length ? `<ol class="artop">${top.rows.slice(0, 8).map((r) => `<li><span>${esc(r.nickname)}</span>${arTier(r.tier)}<b>${r.total}</b></li>`).join("")}</ol>` : `<p class="arempty">${T.empty}</p>`}
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
        <div class="armeta"><span class="arkind ${p.kind}">${p.kind === "short" ? T.short : T.essay}</span><span>${esc(p.subject)}</span><span class="arlv">${arStars(p.level)}</span>
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
    <div class="arpanel">${j.rows.length ? `<table class="cmtbl artbl"><thead><tr><th style="width:56px">#</th><th>${T.nick}</th><th style="width:110px">${T.tier}</th><th style="width:90px">${T.total}</th><th style="width:70px">${T.solved}</th></tr></thead>
      <tbody>${j.rows.map((r) => `<tr class="${cm.me && r.nickname === cm.me.nickname ? "armine" : ""}"><td><b>${r.rank}</b></td><td class="t">${cmAv(r.nickname, "s")} ${esc(r.nickname)}</td><td>${arTier(r.tier)}</td><td><b>${r.total}</b></td><td>${r.solved}</td></tr>`).join("")}</tbody></table>`
      : `<p class="arempty">${T.empty}</p>`}</div>
    <p class="arfoot">${j.tiers.map(([m, n]) => `${arTier(n)} ${m}+`).join(" · ")}</p>`;
}

/* ── my record ── */
async function arMe(root, alive) {
  const T = arT();
  if (!cm.me) { try { sessionStorage.setItem("hlCmBack", "#/me"); } catch (e) {} location.hash = "#/login"; return; }
  const j = await cmApi("GET", "/me/stats"); if (!alive()) return;
  root.innerHTML = `
    <div class="cmtop"><div><h1>${cmAv(cm.me.nickname)} ${esc(cm.me.nickname)} ${arTier(j.tier)}</h1><p>@${esc(cm.me.username)}</p></div>
      <div style="display:flex;gap:6px"><a class="cmbtn sm" href="#/community/account">${T.settings}</a><button class="cmbtn sm" id="arLogout">${T.logout}</button></div></div>
    <div class="arstats"><div><small>${T.myRank}</small><b>${j.rank || "–"}</b></div><div><small>${T.myTotal}</small><b>${j.total}</b></div><div><small>${T.mySolved}</small><b>${j.solved}</b></div></div>
    <div class="arpanel"><h3>${T.recent}</h3>${j.subs.length ? `<table class="cmtbl artbl"><tbody>${j.subs.map((s) => `<tr><td style="width:96px">${esc(s.week)}</td>
      <td class="t"><a href="#/weekly/p/${s.problem_id}">${s.no}. ${esc(lang === "en" ? s.title_en : s.title_ko)}</a></td>
      <td style="width:110px"><b>${s.status === "graded" ? s.score + " / " + s.points : T[s.status] || s.status}</b></td><td style="width:130px">${cmShort(s.created_at)}</td></tr>`).join("")}</tbody></table>` : `<p class="arempty">${T.empty}</p>`}</div>`;
  root.querySelector("#arLogout").onclick = async () => { try { await cmApi("POST", "/logout"); } catch (e) {} cmTok(null); cm.me = null; location.hash = "#/weekly"; arChip(); };
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
        <p class="arempty">answer (short): {"value":1.79,"rel":0.005} or {"value":5.19,"abs":0.02} · rubric (essay): [{"id":"A","name":"…","max":25,"requirement":"…","partial":"…"}] · opens_at/closes_at: unix seconds</p>
        <button class="cmbtn pri" type="submit">${T.save}</button><span class="arinfo"></span></form></div>`;
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
