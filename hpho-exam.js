/* HPhO exam page (#/hpho/exam), modelled on MIPT's online rounds: a technical check, a waiting room, the exam itself with
   one page open and the recording kept continuous, then an hour to upload the answer photos. It runs only inside the
   HaslaEdu desktop app's exam window, whose preload gives it window.haslaExam (the app's name and version, and the
   window's proctoring events). The page sends those events with its own heartbeat to the server
   (community/src/hpho-exam.js); no token or account data passes to the native shell. */
(() => {
  const L = () => (typeof lang === "string" && lang === "en") ? "en" : "ko";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const T = {
    ko: { title: "HPhO 시험", appOnly: "HPhO는 하슬라에듀 데스크톱 앱의 시험 창에서만 응시할 수 있습니다.", appGet: "데스크톱 앱 내려받기",
      check: "기술 점검", checks: { app: "하슬라에듀 데스크톱 앱", net: "서버 연결", entry: "참가 접수", login: "로그인" }, ok: "확인", bad: "문제 있음", wait: "확인 중…",
      notReg: "이 회차에 접수하지 않았습니다.", login: "로그인하세요.", room: "대기실", startsIn: "시험 시작까지", start: "시험 시작", candidate: "수험번호",
      left: "남은 시간", end: "시험 종료", endAsk: "시험을 종료할까요? 종료하면 다시 돌아올 수 없습니다.", rules: ["시험 중에는 이 창만 사용하세요. 다른 프로그램과 웹사이트는 사용할 수 없습니다.", "창을 벗어나거나 화면이 잠기면 기록됩니다. 녹화가 끊기지 않도록 이 창을 유지하세요.", "답안지에는 수험번호만 적으세요."],
      problems: "문제", problemsSoon: "문제는 시험 시작 시각에 이 화면에 공개됩니다.", over: "시험이 끝났습니다", upload: until => `답안 사진은 ${until}까지 올려 주세요.`, conn: "연결", connOk: "정상", connBad: "끊김 · 다시 연결 중", proctor: "감독", proctorOn: "기록 중" },
    en: { title: "HPhO exam", appOnly: "HPhO can only be sat in the exam window of the HaslaEdu desktop app.", appGet: "Get the desktop app",
      check: "Technical check", checks: { app: "HaslaEdu desktop app", net: "Server connection", entry: "Registration", login: "Signed in" }, ok: "OK", bad: "Problem", wait: "Checking…",
      notReg: "You are not registered for this round.", login: "Please sign in.", room: "Waiting room", startsIn: "Exam starts in", start: "Start the exam", candidate: "Candidate number",
      left: "Time left", end: "Finish exam", endAsk: "Finish the exam? You cannot come back once you finish.", rules: ["Use only this window during the exam. Other programs and websites are not allowed.", "Leaving the window or locking the screen is recorded. Keep this window open so the recording stays continuous.", "Write only your candidate number on the answer sheets."],
      problems: "Problems", problemsSoon: "The problems appear here at the start time.", over: "The exam is over", upload: until => `Upload your answer photos by ${until}.`, conn: "Connection", connOk: "Online", connBad: "Lost · reconnecting", proctor: "Proctoring", proctorOn: "Recording" },
  };
  const bridge = () => (window.haslaExam && typeof window.haslaExam.onEvent === "function") ? window.haslaExam : null;
  let st = { round: null, entry: null, session: null, phase: "check", online: true, seq: 0, queue: [], timer: 0, flushTimer: 0, unsub: null };
  const fmt = sec => { sec = Math.max(0, Math.floor(sec)); const h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60; return (h ? h + ":" : "") + String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0"); };
  const skew = () => st.skew || 0, nowS = () => Math.floor(Date.now() / 1000) + skew();
  const path = a => `/hpho/rounds/${encodeURIComponent(st.round.id)}/exam/${a}`;

  function push(kind, detail) {
    try { st.seq = Math.max(st.seq, +sessionStorage.getItem("hphoSeq") || 0) + 1; sessionStorage.setItem("hphoSeq", st.seq); } catch (e) { st.seq++; }
    st.queue.push({ seq: st.seq, t: nowS(), kind, ...(detail ? { detail: String(detail).slice(0, 200) } : {}) });
  }
  async function flush() {
    if (!st.session || st.phase !== "exam") return;
    if (!st.queue.length) push("heartbeat");
    const batch = st.queue.splice(0, 100);
    try { const r = await cmApi("POST", path("events"), { events: batch }); st.online = true; if (r.now) st.skew = r.now - Math.floor(Date.now() / 1000); }
    catch (e) { st.queue.unshift(...batch); st.online = false; if (e?.code === "exam_over") return finish(true); }
    paintBar();
  }

  function view() {
    return `<div class="shell hpho hpho-exam"><div class="hpho-exam-bar" id="hphoExamBar"></div><div id="hphoExamMain"><p class="hpho-muted">…</p></div></div>`;
  }
  function paintBar() {
    const x = T[L()], bar = document.getElementById("hphoExamBar"); if (!bar) return;
    const left = st.session ? st.session.ends_at - nowS() : null;
    bar.innerHTML = `<b class="hpho-exam-title">${x.title}${st.round ? " · " + esc(st.round.title[L()]) : ""}</b>
      ${st.entry ? `<span>${x.candidate} <b class="hpho-no">${esc(st.entry.candidate_no)}</b></span>` : ""}
      ${st.phase === "exam" ? `<span class="hpho-light ${st.online ? "is-ok" : "is-bad"}">${x.conn}: ${st.online ? x.connOk : x.connBad}</span><span class="hpho-light is-ok">${x.proctor}: ${x.proctorOn}</span>
        <span class="hpho-exam-clock${left < 600 ? " is-low" : ""}">${x.left} <b>${fmt(left)}</b></span><button type="button" class="hpho-link" id="hphoExamEnd">${x.end}</button>` : ""}`;
    bar.querySelector("#hphoExamEnd")?.addEventListener("click", () => { if (confirm(x.endAsk)) finish(false); });
  }
  function paint() {
    const x = T[L()], box = document.getElementById("hphoExamMain"); if (!box) return;
    paintBar();
    if (!bridge()) { box.innerHTML = `<section class="hpho-round"><h2>${x.title}</h2><p>${x.appOnly}</p><a class="hpho-btn" href="https://physleague.kr/#/desktop" target="_blank" rel="noopener">${x.appGet}</a></section>`; return; }
    if (st.phase === "check") {
      const c = st.checks || {}, row = k => `<li class="${c[k] === true ? "is-ok" : c[k] === false ? "is-bad" : ""}"><span>${x.checks[k]}</span><b>${c[k] === true ? x.ok : c[k] === false ? x.bad : x.wait}</b></li>`;
      box.innerHTML = `<section class="hpho-round"><h2>${x.check}</h2><ul class="hpho-checks">${["app", "login", "net", "entry"].map(row).join("")}</ul>${st.error ? `<p class="hpho-form-msg">${esc(st.error)}</p>` : ""}</section>`;
      return;
    }
    if (st.phase === "room") {
      const wait = st.round.start_at - nowS();
      box.innerHTML = `<section class="hpho-round hpho-room"><h2>${x.room}</h2><p class="hpho-muted">${x.startsIn}</p><p class="hpho-exam-big">${fmt(wait)}</p>
        <ol class="hpho-exam-rules">${x.rules.map(r => `<li>${r}</li>`).join("")}</ol>
        <button type="button" class="hpho-btn" id="hphoExamStart"${wait > 0 ? " disabled" : ""}>${x.start}</button>${st.error ? `<p class="hpho-form-msg">${esc(st.error)}</p>` : ""}</section>`;
      box.querySelector("#hphoExamStart").addEventListener("click", start);
      return;
    }
    if (st.phase === "exam") {
      if (!box.querySelector(".hpho-paper")) box.innerHTML = `<section class="hpho-round hpho-paper"><h2>${x.problems}</h2><p class="hpho-muted">${x.problemsSoon}</p></section>`;
      return;
    }
    const until = new Date((st.uploadUntil || 0) * 1000).toLocaleString(L() === "en" ? "en-GB" : "ko-KR", { timeStyle: "short", dateStyle: "medium" });
    box.innerHTML = `<section class="hpho-round"><h2>${x.over}</h2><p>${x.upload(esc(until))}</p></section>`;
  }

  async function check() {
    const x = T[L()]; st.checks = { app: !!bridge() }; paint();
    if (!bridge()) return;
    try { await cmLoadMe(); } catch (e) {}
    st.checks.login = !!(typeof cm === "object" && cm && cm.me); paint();
    if (!st.checks.login) { st.error = x.login; return paint(); }
    try {
      const d = await cmApi("GET", "/hpho"); st.checks.net = true;
      st.round = d.rounds.find(r => d.entries?.[r.id] && r.start_at + r.duration_min * 60 > (d.now || nowS())) || null;
      st.entry = st.round ? d.entries[st.round.id] : null; st.checks.entry = !!st.entry; if (d.now) st.skew = d.now - Math.floor(Date.now() / 1000);
      if (!st.entry) { st.error = x.notReg; return paint(); }
      const s = await cmApi("GET", `/hpho/rounds/${encodeURIComponent(st.round.id)}/exam/state`);
      if (s.session?.ended_at) { st.phase = "over"; st.uploadUntil = s.window.upload_until; return paint(); }
      st.phase = "room"; paint();
      if (s.session) start();
    } catch (e) { st.checks.net = false; st.error = e?.code || "network"; paint(); }
  }
  async function start() {
    const b = bridge(); st.error = null;
    try {
      const r = await cmApi("POST", path("start"), { client: b.client });
      st.session = { ends_at: r.ends_at }; st.phase = "exam";
      if (!st.unsub) st.unsub = b.onEvent(e => { if (e && typeof e.kind === "string") push(e.kind, e.detail); });
      push("window_ready", r.resumed ? "resumed" : "started"); b.started?.({ endsAt: r.ends_at });
      clearInterval(st.flushTimer); st.flushTimer = setInterval(flush, 10000); flush(); paint();
    } catch (e) { st.error = e?.code || "network"; paint(); }
  }
  async function finish(byClock) {
    clearInterval(st.flushTimer); if (st.phase !== "exam") return;
    await flush().catch(() => {});
    try { const r = await cmApi("POST", path("end"), {}); st.uploadUntil = r.upload_until; } catch (e) {}
    st.phase = "over"; bridge()?.finished?.({ byClock: !!byClock }); paint();
  }
  function mount() {
    clearInterval(st.timer); st = { ...st, phase: "check", session: null, error: null, queue: [] };
    if (!st.wired) { st.wired = true;
    document.addEventListener("visibilitychange", () => { if (st.phase === "exam") push(document.hidden ? "page_hidden" : "page_visible"); });
    addEventListener("offline", () => { if (st.phase === "exam") push("network_lost"); });
    addEventListener("online", () => { if (st.phase === "exam") { push("network_back"); flush(); } }); }
    check();
    st.timer = setInterval(() => { if (!document.getElementById("hphoExamMain")) return clearInterval(st.timer);
      if (st.phase === "exam" && st.session && nowS() >= st.session.ends_at) finish(true);
      if (st.phase === "room") { const b = document.getElementById("hphoExamStart"), big = document.querySelector(".hpho-exam-big"), w = st.round.start_at - nowS(); if (big) big.textContent = fmt(w); if (b) b.disabled = w > 0; }
      else paintBar(); }, 1000);
  }
  window.HL_HPHO_EXAM = { view, mount };
})();
